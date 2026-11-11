"""A single-table repair cannot erase an explicit cross-table operation.

Source vocabulary disambiguates individual mentions, not every occurrence of a
word. A category called ``join`` must not hide a later request to join tables.
"""
import re

from app.agent.query.tabular_catalog import build_query_tables

_JOIN = re.compile(
    r"\b(?:join(?:ed|ing)?|merg(?:e[ds]?|ing)|match(?:ed|ing)?|combin(?:e[ds]?|ing))\b|"
    r"조인|결합|병합|매칭|연결\s*(?:해서|하여|한|해|하[고여]|해\s*줘|시켜)", re.I,
)
_QUOTED = re.compile(r"'([^']*)'|\"([^\"]*)\"|‘([^’]*)’|“([^”]*)”")
_PREFIX = re.compile(
    r"(?:\b(?:sum|total|average|mean|min|max|count)\s+(?:of\s+)?|"
    r"\b(?:show|list|get)\s+(?:me\s+)?|\b(?:sheet|column|field|category)\s+|"
    r"(?:=|\b(?:is|equals?|contains?))\s*)$", re.I,
)
_SUFFIX = re.compile(
    r"^\s*(?:(?:의|은|는|이|가|을|를|인|별|에서)(?=\s|[?!.,:;]|$)|"
    r"(?:시트|열|항목|값|합계|평균|건수|개수|알려|보여)|"
    r"\b(?:column|sheet|field|value|total|sum|average|count|equals?|is)\b)", re.I,
)
_JOIN_CONTINUATION = re.compile(r"^\s+(?:with|to|using|on|and)\b", re.I)
_MULTIPLE_SOURCES = re.compile(
    r"\b(?:tables|sheets|workbooks|datasets|sources|files)\b|"
    r"(?:두|양쪽|여러|각|모든|[2-9])\s*(?:개(?:의)?\s*)?(?:표|시트|파일)", re.I,
)


def single_table_recovery_allowed(question, summary):
    """Check only recovery eligibility; full request/source validators still run."""
    operations = list(_JOIN.finditer(question))
    if not operations:
        return True
    tables = build_query_tables(summary)
    terms = _source_terms(tables)
    source_spans = []
    quoted = list(_QUOTED.finditer(question))
    for match in quoted:
        value = next(value for value in match.groups() if value is not None)
        if value.strip().casefold() in terms:
            source_spans.append((match.start(), match.end()))
    for term in terms:
        # Keep Korean particles available as source-role evidence, but never
        # match an English field inside another word (e.g. join in rejoined).
        pattern = re.compile(r"(?<![\w])" + re.escape(term) + r"(?![A-Za-z0-9_])", re.I)
        for match in pattern.finditer(question):
            if any(start <= match.start() < end for start, end in
                   ((item.start(), item.end()) for item in quoted)):
                continue
            before, after = question[:match.start()], question[match.end():]
            if _JOIN_CONTINUATION.match(after):
                continue
            if _PREFIX.search(before) or _SUFFIX.match(after):
                source_spans.append((match.start(), match.end()))
    return all(any(start <= operation.start() and operation.end() <= end
                   for start, end in source_spans)
               or _single_table_total_modifier(question, operation, tables)
               for operation in operations)


def _single_table_total_modifier(question, operation, tables):
    # "Combined total" is ordinary sum wording, not a join by itself. This
    # exception cannot hide an explicit multi-source scope or another operation.
    if (operation.group().casefold() != "combined"
            or not re.match(r"^\s+(?:total|sum)\b", question[operation.end():], re.I)
            or _MULTIPLE_SOURCES.search(question)):
        return False
    named = set()
    for table in tables:
        labels = [table.sheet_name, *(value for _, value in table.context
                                     if isinstance(value, str) and len(value.strip()) >= 4)]
        if any(re.search(r"(?<![\w])" + re.escape(label) + r"(?![A-Za-z0-9_])", question, re.I)
               for label in labels if label):
            named.add(table.id)
    return len(named) <= 1


def _source_terms(tables):
    terms = set()
    for table in tables:
        values = [table.sheet_name, *(column.header for column in table.columns)]
        values.extend(value for row in table.rows for value in row.values.values())
        values.extend(value for _, value in table.context)
        terms.update(value.strip().casefold() for value in values
                     if isinstance(value, str) and value.strip() and _JOIN.search(value))
    return terms


def keeps_named_fields(first, revised, summary):
    """A repair fixes a plan; it does not move to a table lacking a field the first reading named.

    "동부 지역 판매금액" was first read as Region and TotalPrice. A repair that sums the East
    column of a Qty summary table drops both. A target that is also a value somewhere (East is
    a Region value) is not counted as a field name.
    """
    tables = build_query_tables(summary)
    normal = lambda value: " ".join(str(value).casefold().split())
    values = {normal(value) for table in tables for row in table.rows for value in row.values.values()
              if isinstance(value, str)}
    headers = {normal(column.header) for table in tables for column in table.columns}
    named = {normal(target) for target in getattr(first, "targets", ())
             if normal(target) in headers and normal(target) not in values}
    if not named:
        return True
    table = next((item for item in tables if item.id == revised.tabular_query.table_id), None)
    return table is not None and named <= {normal(column.header) for column in table.columns}
