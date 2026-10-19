"""Source-anchored rolling calendar windows, independent of numeric values."""
import re
from calendar import monthrange
from datetime import datetime

RELATIVE = re.compile(
    r"최근\s*(\d+)\s*(개월|년|달)(?:간)?(?:\s*동안)?|"
    r"\b(?:(?:over|during|for)\s+(?:the\s+)?)?(?:last|recent|past)\s+(\d+)\s+(years?|months?)\b", re.I,
)
RELATIVE_CUE = re.compile(r"최근|최신|현재|오늘|마지막|어제|지난|"
                          r"\b(?:last|recent|latest|current|today|yesterday|past)\b", re.I)
_DURATION = re.compile(r"\d+\s*(?:개월|년간|달)|\b\d+\s+(?:years?|months?)\b", re.I)


def relative_window(question, observations, has_absolute):
    matches = list(RELATIVE.finditer(question))
    if not matches:
        return None, None, question, None
    if len(matches) != 1 or has_absolute:
        return None, None, question, "상대 기간과 여러 기준일을 함께 해석하지 않았습니다. 하나의 날짜 범위를 지정해 주세요."
    match = matches[0]
    remaining = question[:match.start()] + " " + question[match.end():]
    if RELATIVE_CUE.search(remaining) or _DURATION.search(remaining):
        return None, None, remaining, "상대 기간의 기준이나 길이가 모호합니다. 최근 몇 년 또는 몇 개월인지 하나로 지정해 주세요."
    count = int(match[1] or match[3])
    unit = (match[2] or match[4]).casefold()
    months = count * 12 if unit in {"년", "year", "years"} else count
    if not 0 < months <= 1200 or not observations:
        return None, None, remaining, "상대 기간은 1개월 이상 100년 이하이며 원본의 관측 날짜가 필요합니다."
    try:
        latest = max(item.period for item in observations)
        end = datetime(latest.year, latest.month, latest.day)
        shifted = end.year * 12 + end.month - 1 - months
        year, month_zero = divmod(shifted, 12)
        month = month_zero + 1
        start = datetime(year, month, min(end.day, monthrange(year, month)[1]))
    except (ValueError, TypeError, AttributeError):
        return None, None, remaining, "원본의 최신 관측 날짜에서 상대 기간을 계산하지 못했습니다."
    note = (f"상대 기간은 오늘이 아닌 대상 원본의 최신 관측일 {end.date().isoformat()} 기준입니다. "
            f"조회 범위: {start.date().isoformat()} ~ {end.date().isoformat()}(양끝 포함).")
    return (start, end), note, remaining, None
