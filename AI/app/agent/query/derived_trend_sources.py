"""Select full, original-source operands including an explicit growth baseline."""
from calendar import monthrange
from datetime import datetime

from app.agent.query.metric_request_coverage import _remove_source_phrase
from app.agent.query.tabular_request_scope import explicit_ranges
from app.agent.query.trend_comparison_scope import comparison_candidates
from app.agent.query.trend_date_bounds import parse_trend_date_bounds
from app.agent.query.trend_selection import scoped_trend_candidates, prepare_trend_candidate, distinct_trend_candidates
from app.agent.query.trend_sources import trend_candidates
from app.agent.query.derived_trend_lookback import previous_start


def initial_sources(question, summary, index):
    candidates, named = scoped_trend_candidates(question, trend_candidates(summary, index, question), summary)
    return comparison_candidates(question, candidates), named


def operand_sources(request, question, clean_question, initial, named, summary, index):
    relevant = [candidate for candidate in initial if _label(candidate) in request.labels]
    points = tuple(point for candidate in relevant for point in candidate.observations)
    bounds, error = parse_trend_date_bounds(clean_question, points, named)
    if error:
        return (), None, error
    if request.kind == "growth":
        query = _source_query(question, relevant, request.labels, named)
        prior = previous_start(relevant, summary, index, query) if bounds.start and request.basis == "previous" else None
        query = _expanded_query(query, bounds, request.basis, prior)
        candidates, _ = initial_sources(query, summary, index)
    else:
        candidates = relevant
    candidates = [candidate for candidate in candidates if _label(candidate) in request.labels]
    if not candidates or any(candidate.error for candidate in candidates):
        return (), bounds, "계산할 기간 또는 비교 기준값의 전체 원본을 확인하지 못했습니다. 누락·수식 결과·날짜·대상 범위를 확인해 주세요."
    prepared = [prepare_trend_candidate(candidate, index.rows) for candidate in candidates]
    if any(candidate.error for candidate, _ in prepared):
        return (), bounds, "원본 날짜의 중복·누락 또는 단위·관측 주기 차이로 파생 시계열을 확정하지 못했습니다."
    prepared = distinct_trend_candidates(prepared, preserve_labels=True)
    grouped = {label: [item for item in prepared if _label(item[0]) == label] for label in request.labels}
    if any(len(items) != 1 for items in grouped.values()):
        return (), bounds, "지정한 지표의 원본 후보가 없거나 여러 개입니다. 시트와 표 범위를 지정해 주세요."
    return tuple(grouped[label][0] for label in request.labels), bounds, None


def _label(candidate):
    cell = candidate.observations[0].label if candidate.observations else next(iter(candidate.context), None)
    return str(cell.value) if cell is not None else None


def _source_query(question, candidates, labels, named):
    sources = {str(cell.value) for item in candidates for cell in item.context}
    sources.update(str(cell.value) for item in candidates for point in item.observations for cell in point.entity_cells)
    selected = [value for value in sources if value and _remove_source_phrase(question.casefold(), value) != question.casefold()]
    ranges = [f"'{sheet.replace(chr(39), chr(39) * 2)}'!{reference}" for sheet, reference in explicit_ranges(question)]
    return " and ".join(labels) + " " + " ".join([*named, *selected, *ranges])


def shift_month(date, months):
    year, zero_month = divmod(date.year * 12 + date.month - 1 + months, 12)
    month = zero_month + 1
    # Preserve month-end rather than accidentally comparing February 28 with
    # March 28 when the source explicitly supplies consecutive month ends.
    end = date.day == monthrange(date.year, date.month)[1]
    day = monthrange(year, month)[1] if end else min(date.day, monthrange(year, month)[1])
    return datetime(year, month, day, date.hour, date.minute, date.second, date.microsecond)


def _expanded_query(query, bounds, basis, prior=None):
    start, end = bounds.start, bounds.end
    if start and basis in {"year", "month"}:
        start = shift_month(start, -12 if basis == "year" else -1)
    elif basis == "previous":
        start = prior  # The previous recorded value is not assumed one month old.
    if start and end:
        return f"{query} {start.date().isoformat()} ~ {end.date().isoformat()}"
    if start:
        return f"{query} from {start.date().isoformat()}"
    if end:
        return f"{query} until {end.date().isoformat()}"
    return query
