"""Answer the largest adjacent change in one complete source series."""
import re

from app.agent.query.ambiguity_candidates import clarification_answer
from app.agent.query.change_ranking_request import parse_change_ranking_request
from app.agent.query.single_series_extreme_render import (
    checked_no_movement,
    choice,
    render,
    unavailable,
)
from app.agent.query.trend_calculations import decimal_value, exact_difference
from app.agent.query.trend_selection import (
    distinct_trend_candidates,
    prepare_trend_candidate,
    scoped_trend_candidates,
)
from app.agent.query.trend_sources import trend_candidates

_DIRECTION = re.compile(
    r"(?P<increase>증가|상승|늘(?:어난|었|어|린)|올(?:랐|라|린)|increase|growth|grew|rise|rose|gain)"
    r"|(?P<decrease>감소|하락|줄(?:어든|었|인)|내(?:렸|려|린)|decrease|decline|drop|fell|fall)",
    re.I,
)
_EXTREME = re.compile(
    r"가장\s*(?:많이|크게|큰|높게|높은|낮게|낮은)|제일\s*(?:많이|크게|큰|높게|높은|낮게|낮은)"
    r"|최대|최고|최저|largest|biggest|greatest|most|maximum|max(?:imum)?",
    re.I,
)
_TEMPORAL_TARGET = re.compile(
    r"연도|년도|(?<![가-힣])해(?:는|가|를|에|의|별|마다)?(?=$|[^가-힣])|구간|기간|시점|언제|때|"
    r"year|interval|period|when",
    re.I,
)
_ANNUAL = re.compile(
    r"연도|년도|년\s*단위|(?<![가-힣])해(?:는|가|를|에|의|별|마다)?(?=$|[^가-힣])|전년|year|annual|yearly",
    re.I,
)
_REASONS = {
    "ambiguous_date_axis": "한 지표에 연결할 날짜 축이 여러 개여서 임의로 선택하지 않았습니다.",
    "ambiguous_entity_scope": "서로 다른 회사·부서·지역 또는 시나리오가 섞여 있어 하나의 추이로 연결하지 않았습니다.",
    "missing_entity": "대상을 구분할 값이 비어 있어 같은 대상의 추이인지 확인하지 못했습니다.",
    "missing_or_invalid_value": "기간 중 숫자·수식 결과가 없거나 유효하지 않은 값이 있습니다. 이를 건너뛰거나 0으로 바꾸지 않았습니다.",
    "missing_or_invalid_date": "날짜가 없거나 읽을 수 없는 관측값이 있어 시간순 흐름을 확정하지 못했습니다.",
    "duplicate_period": "같은 날짜에 서로 다른 값이 있어 한 값으로 임의 선택하지 않았습니다.",
    "mixed_series_context": "기간의 길이·실적/예상 구분·단위가 달라 하나의 추이로 연결하지 않았습니다.",
    "conflicting_units": "원본 표시 형식과 단위 설명이 충돌하여 계산 단위를 확정하지 못했습니다.",
    "insufficient_periods": "증감 구간을 계산하려면 서로 다른 날짜의 유효한 값이 두 개 이상 필요합니다.",
    "resource_limit": "전체 시계열 확인 한도를 넘었습니다. 일부 값만 읽고 최대 구간이라고 답하지 않았습니다.",
}


def single_series_extreme_answer(question, summary, index):
    """Return the exact largest adjacent movement, or ``None`` for other intents."""
    request = _request(question)
    if request is None:
        return None
    candidates, _ = scoped_trend_candidates(
        question, trend_candidates(summary, index, question), summary,
    )
    rows = list(index.rows)
    prepared = [prepare_trend_candidate(candidate, rows) for candidate in candidates]
    valid = distinct_trend_candidates(
        [(candidate, units) for candidate, units in prepared if not candidate.error],
        preserve_labels=True,
    )
    if not valid:
        reason = next(
            (_REASONS[candidate.error] for candidate, _ in prepared if candidate.error in _REASONS),
            "요청한 지표의 날짜와 전체 원본 값을 연결하지 못했습니다. 날짜 축과 지표가 있는 표를 지정해 주세요.",
        )
        return unavailable(question, reason)
    if any(candidate.error and candidate.error != "ambiguous_date_axis" for candidate, _ in prepared):
        return unavailable(
            question,
            "같은 항목의 다른 원본 후보에 누락값이나 확인하지 못한 범위가 있습니다. "
            "완전한 표만 임의로 선택하지 않았습니다. 사용할 시트와 표 범위를 지정해 주세요.",
        )
    if len(valid) > 1:
        return clarification_answer(
            question, [choice(question, candidate) for candidate, _ in valid], summary, index,
        )

    candidate, units = valid[0]
    points = candidate.observations
    annual = bool(_ANNUAL.search(question))
    if annual and len({point.period.year for point in points}) != len(points):
        return unavailable(
            question,
            "원본이 연도별 한 값으로 구성되어 있지 않아 월·분기 값을 임의로 연간 값으로 바꾸지 않았습니다. "
            "연간 집계 기준을 지정해 주세요.",
        )
    pairs = [
        (before, after, exact_difference(decimal_value(before.value.value), decimal_value(after.value.value)))
        for before, after in zip(points, points[1:])
        if not annual or after.period.year - before.period.year == 1
    ]
    if not pairs:
        return unavailable(question, "서로 인접한 연도별 원본 값이 없어 연간 증감 구간을 계산하지 못했습니다.")
    direction = request
    eligible = [pair for pair in pairs if pair[2] > 0] if direction == "increase" else [
        pair for pair in pairs if pair[2] < 0
    ]
    if not eligible:
        movement = "증가" if direction == "increase" else "감소"
        return checked_no_movement(question, candidate, units, points, movement)
    target = max(pair[2] for pair in eligible) if direction == "increase" else min(
        pair[2] for pair in eligible
    )
    winners = [pair for pair in eligible if pair[2] == target]
    return render(question, candidate, units, points, winners, direction, annual)


def _request(question):
    # Population rankings (for example, the department with the largest drop)
    # have a different comparison plan and must stay on the ranking engine.
    if parse_change_ranking_request(question) is not None:
        return None
    if not (_EXTREME.search(question) and _TEMPORAL_TARGET.search(question)):
        return None
    directions = [match.lastgroup for match in _DIRECTION.finditer(question)]
    if not directions or len(set(directions)) != 1:
        return None
    return directions[0]
