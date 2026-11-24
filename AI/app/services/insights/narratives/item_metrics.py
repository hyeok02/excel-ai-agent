"""Tables whose rows are different measures (매출 원, 판매수 개, 직원수 명) over a few alternatives in the
columns (계획A · 계획B · 계획C): each measure is compared across the alternatives, never one measure with
another, since 매출 and 직원수 are not amounts of one thing."""
import re

from app.services.insights.narratives.layout_tables import amount, heading, label, span, texts
from app.services.insights.narratives.narrative_values import finite, insight, subject_particle, topic_particle

MEASURES = 3  # the measures read, in the table's order
UNITS = re.compile(r"(?:천|만|백만|억|조)?원|[개명건회대장점일월년주분초%㎡]|시간|박스|세트|톤|kg|g|t|km|m|ℓ|l|ml|ea|pcs|usd|krw|eur|\$", re.I)


def metric_rows(table, key, rows, measures):
    units = _unit_column(table, key, table["rows"])
    if units is None or len(measures) < 2:
        return []
    items = []
    for row in rows:
        values = [(label(table, p), float(row[p]["value"])) for p in measures if finite(row.get(p, {}).get("value"))]
        if len(values) < 2 or len({value for _, value in values}) < 2:
            continue  # 단가 800 in every plan says nothing to compare
        name, unit = " ".join(str(row[key]["value"]).split()), " ".join(str(row.get(units, {}).get("value") or "").split())
        (top, high), (bottom, low) = max(values, key=lambda pair: pair[1]), min(values, key=lambda pair: pair[1])
        said, least = f"{top}({amount(high)}{unit})", f"{bottom}({amount(low)}{unit})"
        fact = (f"‘{name}’{topic_particle(name)} {said}{subject_particle(said)} 가장 많고, "
                f"{least}{subject_particle(least)} 가장 적습니다.")
        cells = [heading(table, p) for p in measures] + [span(table, [row], p) for p in measures if p in row]
        items.append(insight(f"{label(table, key) or '항목'}별 {name}", fact, cells, "metric", topic=name))
        if len(items) == MEASURES:
            break
    return items


def _unit_column(table, key, rows):
    """A text column beside the names holding two or more units ('원', '개', '명'), or None.

    Only units are read as units: '1반' · '2반' or '김민준' beside students are names, not what is counted."""
    for position in sorted(set().union(*rows), reverse=True):  # the one nearest the values: E, not an indented C
        values = texts([row for row in rows if position in row], position) if position != key else None
        if values and len(set(values)) >= 2 and all(UNITS.fullmatch(value.strip()) for value in values):
            return position
    return None
