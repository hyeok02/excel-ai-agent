"""Unresolved calendar qualifiers must not become harmless query vocabulary."""
import re

from app.agent.query.question_dates import MONTH_NAMES

_QUARTER = re.compile(r"\bq[1-4]\b|\b[1-4](?:st|nd|rd|th)?\s+quarter\b|"
                      r"\bquarter\s+[1-4]\b|[1-4]\s*분기", re.I)
_FISCAL = re.compile(r"회계연도|\bfiscal(?:\s+year)?\b|\bfy(?:\b|(?=\d))", re.I)
_SOURCE_FISCAL = re.compile(r"FY\s*(?:19|20)\d{2}(?:\s*[AE])?", re.I)
_MONTH = re.compile(rf"\b(?:{MONTH_NAMES})\b", re.I)


def date_qualifier_error(text, observations, mentions, short_match):
    if _QUARTER.search(text):
        return "특정 분기의 날짜 범위를 확정하지 못했습니다. Q1·Q2 등의 표시 대신 시작월과 종료월을 지정해 주세요."
    if _FISCAL.search(text) and (not observations or any(
        not _SOURCE_FISCAL.fullmatch(str(item.period_cell.value).strip()) for item in observations
    )):
        return "요청한 회계연도의 원본 기간 정의를 확인하지 못했습니다. 달력 연도와 동일하다고 가정하지 않았습니다."
    spans = [(match.start(), match.end()) for match, *_ in mentions]
    if short_match:
        spans.append((short_match.start(), short_match.end()))
    # Replace by position so overlapping short-range/date spans remain safe.
    remaining = list(text)
    for start, end in spans:
        remaining[start:end] = " " * (end - start)
    if _MONTH.search("".join(remaining)):
        return "연도와 연결하지 못한 월 표시가 있습니다. June 2024 또는 2024년 6월처럼 연도와 월을 함께 지정해 주세요."
    return None
