"""Reject only source-proven incompatible detail populations, not sheet names."""
import re

from app.agent.query.comparison_value_format import people_unit
from app.agent.query.metric_observation_periods import LATEST
from app.agent.query.tabular_request_scope import explicit_ranges

_DIMENSIONS = {
    "country": ("country", "countries", "국가", "나라"),
    "region": ("region", "regions", "지역"),
    "department": ("department", "departments", "부서", "부문"),
    "role": ("role", "roles", "직무", "직종"),
}
_ENTITY = re.compile(r"\b(?:company|entity|issuer|organization)\b|회사|기업|법인", re.I)
_TOTAL = re.compile(r"^(?:(?:grand\s+)?total|all|overall|전체|총계|합계)$", re.I)


def unrequested_detail_population(question, table, complete):
    if not complete or not people_unit(question, ""):
        return False
    if not (LATEST.search(question) or re.search(r"전체|총\s*직원|\btotal\b", question, re.I)):
        return False
    if explicit_ranges(question) or table.sheet_name.casefold() in question.casefold():
        return False
    if any(_ENTITY.search(column.header) for column in table.columns):
        return False
    for column in table.columns:
        if column.id in table.hidden_columns:
            continue
        aliases = _dimension_aliases(column.header)
        if not aliases:
            continue
        if any(re.search(r"(?<![a-z])" + re.escape(alias), question, re.I) for alias in aliases):
            continue
        raw = [row.values.get(column.id) for row in table.rows if row.row_number not in table.excluded_rows]
        if any(not isinstance(value, str) for value in raw):
            continue
        values = {value.strip() for value in raw}
        if "" in values or len(values) < 2 or any(_TOTAL.fullmatch(value) for value in values):
            continue
        if any(re.search(r"(?<!\w)" + re.escape(value) + r"(?![a-z0-9])", question, re.I)
               for value in values):
            continue
        return True
    return False


def _dimension_aliases(header):
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", header).casefold()
    text = re.sub(r"(국가|나라|지역|부서|부문|직무|직종)(?:이름|코드|구분|명)", r"\1", text)
    words = set(re.findall(r"[a-z가-힣]+", text)) - {"name", "names", "code", "codes", "id", "and"}
    supported = {alias for aliases in _DIMENSIONS.values() for alias in aliases}
    if not words or not words <= supported:
        return ()
    return tuple(alias for aliases in _DIMENSIONS.values() if words & set(aliases) for alias in aliases)


def absent_source_value(value):
    if value is None:
        return True
    return isinstance(value, str) and (not value.strip() or bool(re.fullmatch(
        r"#(?:PEND|N/A|VALUE!|REF!|DIV/0!|NAME\?|NUM!|NULL!|SPILL!|CALC!)", value.strip(), re.I)))
