"""Bind explicit temporal aggregation grammar without guessing stock/flow intent."""
from dataclasses import dataclass
import re

from app.agent.query.grouped_trend_request_spans import erase_spans, headers_for
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_request_categories import value_matches
from app.agent.query.tabular_request_literals import without_literals
from app.agent.query.trend_source_readback import table_rows

GRAINS = {
    "month": r"월별|월간|매월|\bmonthly\b|\bby\s+month\b",
    "quarter": r"분기별|분기간|매분기|\bquarterly\b|\bby\s+quarter\b",
    "annual": r"연도별|연간|매년|\b(?:yearly|annually|annual)\b|\bby\s+year\b",
}
STATISTICS = {
    "sum": r"합계|총합|\bsum(?:s)?\b",
    "average": r"평균|\b(?:average|mean)\b",
    "min": r"최솟값|최소값|\b(?:minimum|min)\b",
    "max": r"최댓값|최대값|\b(?:maximum|max)\b",
    "last": r"기말(?:값)?|월말(?:값)?|분기말(?:값)?|연말(?:값)?|"
            r"마지막\s*(?:관측값|저장값|값)|\b(?:last\s+(?:observed\s+)?(?:value|observation)|period[ -]end)\b",
}
_UNKNOWN = re.compile(r"중앙값|누적|표준편차|분산|가중|\b(?:median|cumulative|variance|weighted)\b", re.I)


@dataclass(frozen=True)
class ResampledRequest:
    grain: str
    statistic: str
    residual: str
    source_grain: str | None = None


def parse_resampled_request(question, summary, index=None):
    if not any(re.search(pattern, question, re.I) for pattern in GRAINS.values()):
        return None
    tables = build_query_tables(summary)
    protected = [match.span() for table in tables for _, match in headers_for(question, table)]
    values = {sheet.name for sheet in summary.sheets}
    for table in tables:
        if index is None:
            values.update(value for row in table.rows for value in row.values.values() if isinstance(value, str))
        else:
            rows, _ = table_rows(table, tables, index, question)
            values.update(cell.value for row in rows for cell in row.cells if isinstance(cell.value, str))
    for value in values:
        protected.extend(match.span() for match in value_matches(question, value))
    operation = erase_spans(without_literals(question), protected)
    grains = [(name, match) for name, pattern in GRAINS.items()
              for match in re.finditer(pattern, operation, re.I)]
    if not grains:
        return None
    statistics = [(name, match) for name, pattern in STATISTICS.items()
                  for match in re.finditer(pattern, operation, re.I)]
    if not statistics and not _UNKNOWN.search(operation):
        return None
    if len({name for name, _ in grains}) != 1 or len({name for name, _ in statistics}) != 1:
        raise ValueError("묶을 기간과 계산 방식을 각각 하나씩 지정해 주세요. 합계·평균·최솟값·최댓값·마지막 관측값을 지원합니다.")
    if _UNKNOWN.search(operation):
        raise ValueError("요청한 기간 집계 방식을 검증하지 못했습니다. 다른 집계로 바꾸어 답하지 않았습니다.")
    if re.search(r"회계|\bfiscal\b|\bfy\b", operation, re.I):
        raise ValueError("기간 재집계는 달력 기준입니다. 회계 기간의 시작·끝을 임의로 가정하지 않았습니다.")
    spans = [match.span() for _, match in (*grains, *statistics)]
    daily = list(re.finditer(r"일별|일간|\bdaily\b", operation, re.I))
    spans.extend(match.span() for match in daily)
    # Keep labels and predicates intact; only neutral transformation wording is
    # erased after every requested operator has been explicitly accounted for.
    neutral = r"데이터(?:를|는|의)?|관측값(?:을|의)?|묶어서|묶어|집계해서|집계해|\b(?:data|aggregate[d]?|resample|into)\b"
    spans.extend(match.span() for match in re.finditer(neutral, operation, re.I))
    residual = erase_spans(question, spans)
    return ResampledRequest(grains[0][0], statistics[0][0], residual, "day" if daily else None)


def resampling_source_question(request):
    # GroupedSource uses this neutral statistic to activate complete source
    # readback. It is removed before calculation: temporal sum is NOT permission
    # to combine duplicate records on the same original timestamp.
    return request.residual + " 평균 추이"
