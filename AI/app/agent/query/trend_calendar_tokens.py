"""Explicit calendar subperiods, without inferring a year or fiscal offset."""
import re
from dataclasses import dataclass
from calendar import monthrange
from datetime import datetime

from app.agent.query.question_dates import _mentions

_NUMBER = r"[1-4](?:st|nd|rd|th)?|first|second|third|fourth"
_TOKEN = re.compile(
    rf"(?<![a-z])q[1-4](?!\d)|(?:제\s*)?[1-4]\s*분기|"
    rf"\b(?:{_NUMBER})\s+quarter\b|\bquarter\s+[1-4]\b|"
    r"상반기|하반기|(?<![a-z])h[12](?!\d)|\b[12]h(?![a-z])|"
    r"\b(?:first|second|1st|2nd)\s+half(?:\s*[- ]\s*year)?\b", re.I,
)
PERIOD_CUE = re.compile(
    r"(?<![a-z])q\d+(?!\d)|\d+\s*분기|상반기|하반기|\d+\s*반기|"
    r"(?<![a-z])h\d+(?!\d)|\b\d+h\b|"
    r"\b(?:\d+(?:st|nd|rd|th)?|first|second|third|fourth)\s+(?:quarter|half)\b|"
    r"\bquarter\s+\d+\b", re.I,
)
_ADJACENT = re.compile(r"\s*(?:년(?:도)?|도|of)?\s*[-/]?\s*", re.I)
_ORDINAL = {"first": 1, "second": 2, "third": 3, "fourth": 4}


@dataclass(frozen=True)
class CalendarPeriod:
    left: int
    right: int
    start: datetime
    end: datetime


def calendar_periods(text):
    tokens = list(_TOKEN.finditer(text))
    if not tokens:
        return (), "분기·반기의 번호 또는 연도를 확인하지 못했습니다." if PERIOD_CUE.search(text) else None
    mentions, invalid = _mentions(text)
    if invalid or len(tokens) > 2 or not mentions or any(month or day for _, _, month, day in mentions):
        return (), "분기·반기와 결합된 연도 범위를 확인하지 못했습니다. 연도를 포함한 하나의 연속 범위를 지정해 주세요."
    if len(mentions) > len(tokens):
        return (), "분기·반기의 연도 조건이 겹칩니다. 각 기간의 연도를 하나씩 지정해 주세요."
    assigned, used = [], set()
    for token in tokens:
        adjacent = [(match, year) for match, year, _, _ in mentions if (
            match.end() <= token.start() and _ADJACENT.fullmatch(text[match.end():token.start()])
            or token.end() <= match.start() and _ADJACENT.fullmatch(text[token.end():match.start()])
        )]
        if len(adjacent) > 1:
            return (), "같은 분기·반기에 여러 연도가 연결되어 있습니다."
        if adjacent:
            match, year = adjacent[0]
            used.add(match.span())
        elif len(mentions) == 1 and len(tokens) == 2:
            match, year = mentions[0][:2]
        else:
            return (), "각 분기·반기의 연도가 필요합니다. 원본의 연도를 임의로 선택하지 않았습니다."
        left, right = (min(token.start(), match.start()), max(token.end(), match.end())) if adjacent else token.span()
        start, end = _bounds(token[0], year)
        assigned.append(CalendarPeriod(left, right, start, end))
    if used != {match.span() for match, *_ in mentions}:
        return (), "분기·반기와 연결되지 않은 연도가 있습니다."
    remaining = text
    for period in sorted(assigned, key=lambda item: item.left, reverse=True):
        remaining = remaining[:period.left] + " " * (period.right - period.left) + remaining[period.right:]
    if PERIOD_CUE.search(remaining):
        return (), "일부 분기·반기 조건을 해석하지 못했습니다."
    return tuple(assigned), None


def _bounds(token, year):
    value = token.casefold()
    half = any(word in value for word in ("반기", "half", "h")) and "quarter" not in value
    if "상반기" in value:
        number = 1
    elif "하반기" in value:
        number = 2
    elif match := re.search(r"[1-4]", value):
        number = int(match[0])
    else:
        number = next(number for word, number in _ORDINAL.items() if word in value)
    length = 6 if half else 3
    start_month, end_month = (number - 1) * length + 1, number * length
    return datetime(year, start_month, 1), datetime(year, end_month, monthrange(year, end_month)[1])
