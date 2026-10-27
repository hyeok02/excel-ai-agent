"""Bind population controls to source measure meaning and explicit total labels."""
import re

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.metric_observation_units import _currency
from app.agent.query.metric_semantics import people_number_formats

ROLE_HEADERS = {"row role", "row type", "record type", "행 구분", "행 유형"}
_TOTAL = r"(?:sub[ -]?total|grand total|total|소계|총계|합계|총합계|총합)"
_TOTAL_END = re.compile(r"(?:^|[\s:])" + _TOTAL + r"\s*$", re.I)
_TOTAL_START = re.compile(r"^" + _TOTAL + r"\s+(?:of\s+)?(.+)$", re.I)
_MONEY = re.compile(r"\b(?:revenue|sales|amount|cost|price|income|profit|balance|cash|assets?|debt|tax)\b|"
                    r"매출|금액|원가|비용|이익|가격|부채|자산|현금", re.I)
_COUNT = re.compile(r"\b(?:employees?|headcount|fte|quantity|count|units sold)\b|인원|직원\s*수|수량|판매량|건수|개수", re.I)


def uses_currency(column):
    """An adjacent report currency cannot turn employees or quantities into money."""
    specs = [parse_number_format(style) for style in column.number_formats]
    if _currency(column.header) or any(_currency(spec.prefix + spec.suffix) for spec in specs):
        return True
    if specs and all(spec.percent for spec in specs):
        return False
    if people_number_formats(column):
        return False
    if _MONEY.search(column.header):
        return True
    return not bool(_COUNT.search(column.header))


def row_population_role(row, table):
    numeric_headers = {_normal(column.header) for column in table.columns
                       if any(isinstance(value, (int, float)) and not isinstance(value, bool)
                              for value in column.sample_values)}
    explicit = [str(row.values.get(column.id) or "").strip()
                for column in table.columns if column.header.strip().casefold() in ROLE_HEADERS]
    marker = any(_total_marker(value, numeric_headers) for column, value in row.values.items()
                 if not any(item.id == column and item.header.strip().casefold() in ROLE_HEADERS
                            for item in table.columns))
    formula = any(re.search(r"(?<!\w)(?:SUBTOTAL|AGGREGATE)\s*\(", value, re.I)
                  for value in row.formulas.values())
    stated_total = any(_TOTAL_END.search(value) for value in explicit)
    stated_detail = any(value.casefold() in {"detail", "details", "상세", "개별", "invoice", "credit note"}
                        for value in explicit)
    if (marker or formula) and stated_detail:
        return None
    return "total" if marker or formula or stated_total else "detail"


def _total_marker(value, headers):
    if not isinstance(value, str):
        return False
    text = value.strip()
    if _TOTAL_END.search(text):
        return True
    prefix = _TOTAL_START.fullmatch(text)
    return bool(prefix and _normal(prefix[1]) in headers)


def _normal(value):
    return re.sub(r"[\W_]+", " ", value.casefold()).strip()
