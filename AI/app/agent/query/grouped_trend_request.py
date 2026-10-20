"""Bind conditional/grouped trend grammar to this workbook's original schema."""
from dataclasses import dataclass
import re

from app.agent.query.grouped_trend_conditions import categorical_conditions, numeric_conditions
from app.agent.query.grouped_trend_request_spans import erase_spans, grouping_spans, headers_for
from app.agent.query.tabular_query_models import TabularFilter
from app.agent.query.tabular_request_literals import without_literals

_STATISTICS = {
    "sum": r"합계|총합|\bsum\b", "average": r"평균|\b(?:average|mean)\b",
    "min": r"최솟값|최소값|\bminimum\b", "max": r"최댓값|최대값|\bmaximum\b",
}


@dataclass(frozen=True)
class GroupedTrendRequest:
    groups: tuple[str, ...]
    filters: tuple[TabularFilter, ...]
    statistic: str | None
    residual: str
    description: str


def parse_grouped_request(question, table, records, metric_id, date_id):
    headers = headers_for(question, table)
    groups, spans = grouping_spans(question, headers)
    filters, category_spans = categorical_conditions(question, table, records, headers, metric_id, date_id)
    numeric_filters, numeric_spans = numeric_conditions(erase_spans(question, category_spans), headers)
    filters.extend(numeric_filters)
    spans.extend([*category_spans, *numeric_spans])
    # Operation words inside source headers or quoted literal values are data.
    operation_text = erase_spans(without_literals(question),
                                 [*[match.span() for _, match in headers], *category_spans, *numeric_spans])
    statistics = [(name, match) for name, pattern in _STATISTICS.items()
                  for match in re.finditer(pattern, operation_text, re.I)]
    if not groups and not filters and not statistics:
        return None
    if re.search(r"\b(?:or|either)\b|또는|혹은", operation_text, re.I):
        raise ValueError("여러 조건을 또는으로 연결한 추이는 아직 확인할 수 없습니다. 조건을 하나씩 지정해 주세요.")
    if len(groups) > 3 or set(groups) & {metric_id, date_id}:
        raise ValueError("추이의 날짜·수치 열과 구분할 그룹 열을 별도로 지정해 주세요. 그룹 열은 3개까지 지원합니다.")
    if len({name for name, _ in statistics}) > 1:
        raise ValueError("같은 추이에 적용할 집계 방식을 하나로 지정해 주세요.")
    if len(filters) > 8:
        raise ValueError("한 번에 확인할 조건을 8개 이하로 지정해 주세요.")
    spans.extend(match.span() for _, match in statistics)
    residual = erase_spans(question, spans)
    # These tokens merely attach an already bound predicate to a query.
    if filters:
        residual = re.sub(r"\b(?:where|only)\b", " ", residual, flags=re.I)
    statistic = statistics[0][0] if statistics else None
    names = {column.id: column.header for column in table.columns}
    descriptions = [f"그룹: {', '.join(names[key] for key in groups)}"] if groups else []
    descriptions.extend(f"조건: {names[item.column_id]} {item.operator} {item.value}" for item in filters)
    if statistic:
        descriptions.append(f"각 시점 집계: {statistic}")
    return GroupedTrendRequest(groups, tuple(filters), statistic, residual, "; ".join(descriptions))
