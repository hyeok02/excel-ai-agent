"""Tables set side by side on one sheet over the same items: 지점별 인원 | 지점별 매출.

Each table's largest and smallest item is read, and when one of them counts people, the other's
value per person.
"""
import re

from app.services.insights.narratives.layout_tables import (
    NONADDITIVE, amount, heading, kept_rows, noted, label, numbers, sheet_tables, span, texts,
)
from app.services.insights.narratives.narrative_values import insight, subject_particle, topic_particle

_PEOPLE = re.compile(r"\b(?:headcount|employees|staff|members)\b|인원|직원\s*수|사원\s*수|인력", re.I)


def side_table_report(context):
    for sheet in context.get("sheets", []):
        tables = [table for table in sheet_tables(sheet) if len(table["header"]) == 1]
        read = [found for table in tables if (found := _read(table))]
        for index, one in enumerate(read):
            other = next((item for item in read[index + 1:] if set(item[2]) == set(one[2])), None)
            if other is not None:
                return _report(one, other)
    return [], ""


def _read(table):
    """(table, rows, names, measure) when the table is items and one numeric column."""
    key = min(table["header"][0])
    rows = kept_rows(table, key)
    names = texts(rows, key)
    measures = [p for p in sorted(table["header"][0]) if p != key and numbers(rows, p)]
    if not names or len(set(names)) != len(names) or len(names) < 3 or len(measures) != 1:
        return None
    return table, rows, names, measures[0], key


def _what(table, p):
    return label(table, p)


def _report(one, other):
    items, tops = [], []
    for table, rows, names, p, key in (one, other):
        values = dict(zip(names, numbers(rows, p)))
        high, low = max(values, key=values.get), min(values, key=values.get)
        top = f"{high}({amount(values[high], table['unit'])})"
        bottom = f"{low}({amount(values[low], table['unit'])})"
        what = _what(table, p)
        fact = noted(f"{what}{topic_particle(what)} {top}{subject_particle(top)} 가장 많고, "
                     f"{bottom}{subject_particle(bottom)} 가장 적습니다.", table["unit"])
        cited = [heading(table, p), span(table, rows, p), span(table, rows, key)]
        items.append(insight(f"{label(table, key)}별 {what}", fact, cited, "metric", topic=what))
        tops.append(f"{what}{topic_particle(what)} {high}")
    per = _per_person(one, other) or _per_person(other, one)
    if per:
        items.append(per)
    last = tops[1].rsplit(" ", 1)[1]
    return items, f"{tops[0]}, {tops[1]}{subject_particle(last)} 가장 많습니다."


def _per_person(people, amounts):
    table, rows, names, p, key = people
    other, other_rows, other_names, q, other_key = amounts
    if not _PEOPLE.search(_what(table, p)) or _PEOPLE.search(_what(other, q)) or NONADDITIVE.search(_what(other, q)):
        return None
    heads, values = dict(zip(names, numbers(rows, p))), dict(zip(other_names, numbers(other_rows, q)))
    per = {name: values[name] / heads[name] for name in names if heads[name]}
    if len(per) < 3:
        return None
    high, low = max(per, key=per.get), min(per, key=per.get)
    unit = other["unit"]
    top, bottom = f"{high}({amount(per[high], unit)})", f"{low}({amount(per[low], unit)})"
    what = f"1인당 {_what(other, q)}"
    fact = noted(f"{what}{topic_particle(what)} {top}{subject_particle(top)} 가장 높고, "
                 f"{bottom}{subject_particle(bottom)} 가장 낮습니다.", unit)
    cited = [heading(table, p), span(table, rows, p), heading(other, q), span(other, other_rows, q),
             span(table, rows, key), span(other, other_rows, other_key)]
    return insight(what, fact, cited, "metric", topic=_what(other, q))

