"""Recognize questions asking for the observed time-series period."""
import re

START_WORDS = ("몇 년부터", "언제부터", "시작 시점", "시작일", "start date", "since when")
PERIOD_WORDS = (
    "어느 기간", "데이터 기간", "분석 기간", "조회 기간", "기간은", "기간이",
    "기간을 알려", "기간 알려", "date range", "what period",
)


# "근속 기간", "계약 기간" name a source field; only these words scope the data.
_DATA_SCOPES = ("데이터", "분석", "조회", "어느", "전체", "수집", "기록", "시계열", "관측", "자료", "파일")


def build_metric_period(comparison: object, question: str) -> dict[str, object] | None:
    normalized = question.casefold()
    if not any(word in normalized for word in START_WORDS) and not (
        any(word in normalized for word in PERIOD_WORDS) and _asks_data_period(normalized)
    ):
        return None
    if not isinstance(comparison, dict):
        return None
    start = comparison.get("start_date")
    end = comparison.get("end_date")
    start_reference = comparison.get("start_reference")
    end_reference = comparison.get("end_reference")
    if not all(isinstance(value, str) for value in (start, end, start_reference, end_reference)):
        return None
    return {
        "start_date": start,
        "end_date": end,
        "start_reference": start_reference,
        "end_reference": end_reference,
        "metric_group": comparison.get("metric_group"),
    }


def _asks_data_period(text: str) -> bool:
    if "date range" in text or "what period" in text:
        return True
    for match in re.finditer(r"([가-힣]+)?\s*기간", text):
        before = re.sub(r"(?:의|에|은|는)$", "", match.group(1) or "")
        if not before or before.endswith(_DATA_SCOPES):
            return True
    return False
