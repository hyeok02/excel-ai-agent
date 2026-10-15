"""Verify model-selected names against question text and source header cells."""
import re
import unicodedata
from itertools import product
from openpyxl.utils import range_boundaries

from app.agent.query.header_relation_models import HeaderRelationPlan

_PARTICLE = r"(?:에서|으로|이랑|하고|은|는|을|를|이|가|의|과|와|랑|도|만|로|별)?"
_RELATION = re.compile(r"같|동일|차이|다르|다른|구분|묶|별개|한\s*(?:열|항목)|"
                       r"\b(?:same|different|difference|equivalent|separate|together)\b", re.I)
_STRUCTURE = re.compile(r"항목|열|헤더|명칭|이름|뜻|의미|\b(?:headers?|columns?|fields?|names?|meaning)\b", re.I)
_VALUES = re.compile(r"값|수치|건수|개수|몇\s*(?:개|건|명)|합계|평균|최대|최소|얼마|수식|"
                     r"같은\s*행|다른\s*행|행\s*(?:만|별|목록|개수)|"
                     r"증감|증가|감소|상위|하위|목록|나열|\b(?:values?|counts?|sum|"
                     r"average|total|top|bottom|list|greater|less|increase|decrease|rows?|records?|formulas?)\b", re.I)


def normal(text):
    return unicodedata.normalize("NFKC", str(text)).casefold().strip()


def mention_spans(mention, text):
    tokens = re.findall(r"\w+|[^\w\s]", normal(mention))
    if not tokens or not any(character.isalnum() for character in mention):
        return []
    expression = r"\s*".join(re.escape(token) for token in tokens)
    pattern = r"(?<![\w])(" + expression + ")" + _PARTICLE + r"(?![\w])"
    return [match.span(1) for match in re.finditer(pattern, normal(text))]


def independent_mentions(mentions, text):
    if len(mentions) != 2 or normal(mentions[0]) == normal(mentions[1]):
        return False
    return any(a[1] <= b[0] or b[1] <= a[0]
               for a, b in product(*(mention_spans(name, text) for name in mentions)))


def relation_request(question, intent, mentions=()):
    remaining = normal(question)
    for mention in mentions:
        remaining = normal(remaining)
        for start, end in reversed(mention_spans(mention, remaining)):
            remaining = remaining[:start] + " " * (end - start) + remaining[end:]
    if _VALUES.search(remaining):
        return False
    return bool(_RELATION.search(remaining) or getattr(intent, "kind", "") == "field_relation")


def scoped_tables(question, tables):
    named = {table.sheet_name for table in tables if mention_spans(table.sheet_name, question)}
    contexts = {text for table in tables for _, text in table.context
                if len(text) >= 4 and mention_spans(text, question)}
    ranges = _source_ranges(question, {table.sheet_name for table in tables})
    return [table for table in tables
            if (not named or table.sheet_name in named)
            and (not contexts or contexts <= {text for _, text in table.context})
            and (not ranges or all(sheet == table.sheet_name and _inside(reference, table.reference)
                                   for sheet, reference in ranges))]


def headers_in_requested_ranges(question, table, columns):
    ranges = _source_ranges(question, {table.sheet_name})
    return not ranges or all(any(sheet == table.sheet_name and _inside(
        column.header_reference.rsplit("!", 1)[1], reference) for sheet, reference in ranges)
        for column in columns)


def _source_ranges(question, sheets):
    names = "|".join(re.escape(name) for name in sorted(sheets, key=len, reverse=True))
    pattern = (r"(?<![\w'])('(?:" + names + r")'|(?:" + names + r"))!"
               r"\$?([A-Za-z]{1,3}\$?[1-9]\d*)(?::\$?([A-Za-z]{1,3}\$?[1-9]\d*))?")
    found = [(sheet.strip("'"), first.upper() + (":" + last.upper() if last else ""))
             for sheet, first, last in re.findall(pattern, question)] if sheets else []
    # Unknown explicit sheets may not silently disappear from the request.
    count = len(re.findall(r"!\$?[A-Za-z]{1,3}\$?[1-9]\d*", question))
    return found if len(found) == count else [("", "")]


def _inside(inner, outer):
    try:
        a, b, c, d = range_boundaries(inner.replace("$", ""))
        e, f, g, h = range_boundaries(outer.replace("$", ""))
        return e <= a <= c <= g and f <= b <= d <= h
    except (TypeError, ValueError):
        return False


def matching_columns(table, mentions, cells):
    options = [[column for column in table.columns
                if mention_spans(mention, column.header)
                and (cell := cells.get(column.header_reference)) is not None
                and not cell.formula and normal(cell.value) == normal(column.header)]
               for mention in mentions]
    results = {}
    for first, second in product(*options):
        if first.id == second.id and not independent_mentions(mentions, first.header):
            continue
        columns = tuple(dict.fromkeys((first, second)))
        if len({column.header_reference for column in columns}) != len(columns):
            continue
        results[tuple(column.id for column in columns)] = columns
    return list(results.values())


def fallback_plans(question, tables, cells, allow_separate=False):
    """When classification is unavailable, use only whole source label parts."""
    result = []
    for table in tables:
        names = set()
        for column in table.columns:
            parts = re.split(r"[,，/·ㆍ&+]|\band\b", column.header, flags=re.I)
            for name in [column.header, *parts]:
                if (name := name.strip()) and mention_spans(name, question):
                    names.add(name)
        names = sorted(name for name in names if not any(
            name != other and normal(name) in normal(other) for other in names))
        if len(names) != 2 or not independent_mentions(names, question):
            continue
        for columns in matching_columns(table, names, cells):
            # Without a semantic intent, "A and B the same?" can mean values.
            if len(columns) > 1 and not allow_separate and not _STRUCTURE.search(question):
                continue
            result.append(HeaderRelationPlan(table_id=table.id,
                          column_ids=[column.id for column in columns], mentions=names))
    return result
