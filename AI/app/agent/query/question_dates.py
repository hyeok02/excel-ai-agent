"""Extract bounded calendar periods from Korean and English questions."""

import re
from calendar import monthrange
from datetime import datetime

MONTHS = {
    name: number
    for number, names in enumerate((
        ("january", "jan"), ("february", "feb"), ("march", "mar"),
        ("april", "apr"), ("may",), ("june", "jun"), ("july", "jul"),
        ("august", "aug"), ("september", "sep", "sept"),
        ("october", "oct"), ("november", "nov"), ("december", "dec"),
    ), start=1)
    for name in names
}
MONTH_NAMES = "|".join(MONTHS)
KOREAN = re.compile(
    r"(?<!\d)((?:19|20)\d{2})\s*년"
    r"(?:\s*(\d{1,2})\s*월(?:\s*(\d{1,2})\s*일)?)?"
)
ISO = re.compile(r"(?<!\d)((?:19|20)\d{2})[./-](\d{1,2})[./-](\d{1,2})(?!\d)")
YEAR_MONTH = re.compile(r"(?<!\d)((?:19|20)\d{2})[./-](\d{1,2})(?!\d|[./-]\d)")
MONTH_DAY_YEAR = re.compile(
    rf"\b({MONTH_NAMES})\s+(\d{{1,2}})(?:st|nd|rd|th)?\s*,?\s*((?:19|20)\d{{2}})\b",
    re.I,
)
DAY_MONTH_YEAR = re.compile(
    rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTH_NAMES})\s*,?\s*((?:19|20)\d{{2}})\b",
    re.I,
)
MONTH_YEAR_DAY = re.compile(
    rf"\b({MONTH_NAMES})\s+((?:19|20)\d{{2}})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b",
    re.I,
)
MONTH_YEAR = re.compile(rf"\b({MONTH_NAMES})\s+((?:19|20)\d{{2}})\b", re.I)
KOREAN_RANGE = re.compile(
    r"(?<!\d)((?:19|20)\d{2})\s*년\s*(\d{1,2})\s*월\s*부터\s*(\d{1,2})\s*월\s*까지"
)
ENGLISH_RANGE = re.compile(
    rf"\bfrom\s+({MONTH_NAMES})\s+(?:to|through|until)\s+"
    rf"({MONTH_NAMES})\s+((?:19|20)\d{{2}})\b",
    re.I,
)
START_WORDS = ("부터", "이후", "from", "since", "after")
END_WORDS = ("까지", "이전", "through", "until", "before")
INVALID_BOUNDS = (datetime.max, datetime.min)


def question_date_bounds(query: str) -> tuple[datetime | None, datetime | None]:
    if (shortened := _short_range(query)) is not None:
        return shortened
    mentions, invalid = _mentions(query)
    if invalid:
        return INVALID_BOUNDS
    if len(mentions) >= 2:
        return _date(mentions[0], False), _date(mentions[1], True)
    if not mentions:
        return None, None
    mention = mentions[0]
    direction = _direction(query, mention[0])
    if direction == "start":
        return _date(mention, False), None
    if direction == "end":
        return None, _date(mention, True)
    return _date(mention, False), _date(mention, True)


def requested_calendar_period(
    query: str,
) -> tuple[int, int | None, int | None] | None:
    if _short_range(query) is not None:
        return None
    mentions, invalid = _mentions(query)
    if invalid or len(mentions) != 1:
        return None
    _, year, month, day = mentions[0]
    return year, month, day


def _short_range(query: str) -> tuple[datetime, datetime] | None:
    if match := KOREAN_RANGE.search(query):
        year, start, end = (int(value) for value in match.groups())
    elif match := ENGLISH_RANGE.search(query):
        start, end = (MONTHS[match.group(i).casefold()] for i in (1, 2))
        year = int(match.group(3))
    else:
        return None
    if not 1 <= start <= 12 or not 1 <= end <= 12 or start > end:
        return INVALID_BOUNDS
    return datetime(year, start, 1), datetime(year, end, monthrange(year, end)[1])


def _mentions(query: str) -> tuple[list[tuple[re.Match, int, int | None, int | None]], bool]:
    found = []
    patterns = (
        (ISO, lambda m: (int(m[1]), int(m[2]), int(m[3]))),
        (YEAR_MONTH, lambda m: (int(m[1]), int(m[2]), None)),
        (KOREAN, lambda m: (int(m[1]), _integer(m[2]), _integer(m[3]))),
        (MONTH_DAY_YEAR, lambda m: (int(m[3]), MONTHS[m[1].casefold()], int(m[2]))),
        (DAY_MONTH_YEAR, lambda m: (int(m[3]), MONTHS[m[2].casefold()], int(m[1]))),
        (MONTH_YEAR_DAY, lambda m: (int(m[2]), MONTHS[m[1].casefold()], int(m[3]))),
        (MONTH_YEAR, lambda m: (int(m[2]), MONTHS[m[1].casefold()], None)),
    )
    for pattern, values in patterns:
        for match in pattern.finditer(query):
            if any(_overlap(match, item[0]) for item in found):
                continue
            year, month, day = values(match)
            found.append((match, year, month, day))
    invalid = any(not _valid(item) for item in found)
    valid = sorted((item for item in found if _valid(item)), key=lambda item: item[0].start())
    return valid, invalid


def _overlap(left: re.Match, right: re.Match) -> bool:
    return left.start() < right.end() and right.start() < left.end()


def _integer(value: str | None) -> int | None:
    return int(value) if value else None


def _valid(mention) -> bool:
    _, year, month, day = mention
    if month is not None and not 1 <= month <= 12:
        return False
    return day is None or month is not None and 1 <= day <= monthrange(year, month)[1]


def _date(mention, end: bool) -> datetime:
    _, year, month, day = mention
    month = month or (12 if end else 1)
    day = day or (monthrange(year, month)[1] if end else 1)
    return datetime(year, month, day)


def _direction(query: str, match: re.Match) -> str | None:
    context = query[max(0, match.start() - 8) : match.end() + 8].casefold()
    if any(word in context for word in START_WORDS):
        return "start"
    if any(word in context for word in END_WORDS):
        return "end"
    return None
