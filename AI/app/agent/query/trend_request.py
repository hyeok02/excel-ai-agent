"""Recognize temporal trajectories without authorizing unrelated calculations."""
import re

from app.agent.query.metric_request_coverage import uncovered_request_tokens
from app.agent.query.metric_observation_periods import GRAINS
from app.agent.query.trend_labels import trend_label_spellings
from app.agent.query.trend_date_bounds import parse_trend_date_bounds, select_trend_periods
from app.agent.query.trend_postconditions import trend_postcondition_error

_TREND = re.compile(r"추이|추세|흐름|반등|상승\s*전환|하락\s*전환|"
                    r"\b(?:trends?|trajectory|rebound|time\s+series|over\s+time)\b", re.I)
_RANGE_ONLY = re.compile(r"몇\s*년부터|언제부터|언제까지|시작\s*(?:연도|날짜)|데이터\s*기간")
_PERIODIC = re.compile(r"(?:기간|시점|날짜|연도|월|분기)별.{0,40}(?:변화|증감|변동)")
_GRAMMAR = re.compile(r"기간별|시점별|날짜별|분기별|월별|연도별|시간순|날짜순|연대순|시계열|전체\s*기간|"
                      r"각\s*시점|꾸준히|계속|지속적으로|\b(?:chronological|chronologically|and)\b", re.I)
_UNSUPPORTED = re.compile(
    r"평균|합계|총합|누적|중앙값|분산|표준편차|예측|전망|내년|내달|"
    r"부서별|직무별|항목별|지역별|각\s*(?:부서|직무|항목)|"
    r"이상|이하|초과|미만|제외|포함|조건|나누|대비|왜|원인|이유|[<>]|"
    r"최근|최신|현재|마지막\s*\d|이후|이전|\d+\s*(?:개월|년간)|"
    r"\b(?:sum|average|mean|median|ratio|forecast|predict|why|cause|"
    r"latest|recent|last|current|since|after|before|excluding|only|where|or)\b", re.I,
)


def asks_trend(question):
    return not _RANGE_ONLY.search(question) and bool(_TREND.search(question) or _PERIODIC.search(question))


def trend_request_error(question, observations, named_sheets):
    bounds, error = parse_trend_date_bounds(question, observations, named_sheets)
    if error:
        return error
    # Source labels may themselves contain operation words (e.g. Revenue Growth).
    # Mask only actual selected labels before rejecting an unimplemented request.
    remaining = bounds.remainder
    labels = {label for item in observations for label in trend_label_spellings(item.label.value)}
    for label in sorted(labels, key=len, reverse=True):
        remaining = re.sub(r"(?<!\w)" + re.escape(label) + r"(?![a-z0-9])", " ", remaining, flags=re.I)
    if error := trend_postcondition_error(remaining, observations, named_sheets):
        return error
    if _UNSUPPORTED.search(remaining) or re.search(r"증가율|감소율|증감률|비율|비중|점유율|기여율|"
                                                   r"%|\b(?:growth\s+rate|rate|ratio|share|percentage|percent)\b", remaining, re.I):
        return "추이 외의 조건·집계까지 함께 확인할 수 없습니다. 대상과 비교할 날짜 범위를 구체적으로 지정해 주세요."
    requested = {key for key, pattern in GRAINS.items() if pattern.search(remaining)}
    if requested and not _cadence_matches(requested, observations):
        return "요청한 월별·분기별·연도별 구분과 원본 관측 주기가 다릅니다. 기간을 임의로 합산하거나 다른 주기의 값으로 대신하지 않았습니다."
    remainder = _GRAMMAR.sub(" ", _TREND.sub(" ", remaining))
    for label in {str(item.label.value) for item in observations}:
        spellings = trend_label_spellings(label)
        for spelling in spellings[1:]:
            remainder = re.sub(re.escape(spelling), label, remainder)
    missing = uncovered_request_tokens(remainder, observations, named_sheets)
    if missing:
        return "질문의 항목·대상·조건을 원본 시계열과 모두 연결하지 못했습니다. 원본 항목명과 범위를 확인해 주세요."
    return None


def _cadence_matches(requested, observations):
    if len(requested) != 1:
        return False
    kind = next(iter(requested))
    if all(item.grain == kind for item in observations):
        return True
    if any(item.grain is not None for item in observations) or kind not in {"annual", "quarter", "month"}:
        return False
    # Regular source snapshots can be shown at their observed cadence. Never
    # resample daily/quarterly data into an unrequested sum or average.
    dates = sorted({item.period for item in observations})
    step = {"annual": 12, "quarter": 3, "month": 1}[kind]
    months = [date.year * 12 + date.month for date in dates]
    return len(months) >= 2 and all(right - left == step for left, right in zip(months, months[1:]))


def bound_trend_periods(question, observations, named_sheets=()):
    bounds, error = parse_trend_date_bounds(question, observations, named_sheets)
    if error:
        return (), error
    selected = select_trend_periods(observations, bounds)
    if len({item.period for item in selected}) < 2:
        return (), "요청한 범위에서 서로 다른 날짜의 유효한 값이 두 개 이상 필요합니다."
    return selected, None
