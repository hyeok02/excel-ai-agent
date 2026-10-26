"""Resolve and disclose a trend's date window before validating its values."""
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.agent.query.question_dates import (
    _mentions, _date, _short_range, question_date_bounds, KOREAN_RANGE, ENGLISH_RANGE,
)
from app.agent.query.trend_period_scope import calendar_request
from app.agent.query.trend_relative_dates import relative_window, RELATIVE_CUE
from app.agent.query.trend_date_qualifiers import date_qualifier_error
from app.agent.query.trend_calendar_periods import expand_calendar_periods

_POST = re.compile(r"^\s*(이후|이전|부터|까지|에서|으로|로)(?=$|\s|[가-힣])")
_PRE = re.compile(r"\b(from|since|after|through|until|before)\s*$", re.I)
_DATE_WORDS = re.compile(r"이후|이전|부터|까지|\b(?:from|since|after|through|until|before)\b", re.I)
_UNSUPPORTED_DATE = re.compile(r"작년|재작년|올해|금년|내년|지난달|이번달|이달|금월|내달|"
                               r"분기\s*(?:이후|이전)|\d+\s*(?:개월|년간)|"
                               r"\b(?:last|next|this)\s+(?:year|month|quarter)\b", re.I)


@dataclass(frozen=True)
class TrendDateBounds:
    start: datetime | None = None
    end: datetime | None = None
    note: str = ""
    relative: bool = False
    remainder: str = ""


def parse_trend_date_bounds(question, observations, named_sheets=()):
    masked, error = calendar_request(question, observations, named_sheets)
    if error:
        return None, error
    masked, calendar_note, error = expand_calendar_periods(masked)
    if error:
        return None, error
    mentions, invalid = _mentions(masked)
    if invalid:
        return None, "요청한 날짜가 달력에 존재하지 않습니다."
    short_match = KOREAN_RANGE.search(masked) or ENGLISH_RANGE.search(masked)
    if error := date_qualifier_error(masked, observations, mentions, short_match):
        return None, error
    window, note, remaining, error = relative_window(masked, observations, bool(mentions))
    if error:
        return None, error
    if window:
        return TrendDateBounds(*window, note, True, remaining), None
    if RELATIVE_CUE.search(masked) or _UNSUPPORTED_DATE.search(masked):
        return None, "상대 기간의 기준이 모호하거나 지원하지 않는 기간입니다. 최근 1년·6개월 또는 날짜 범위를 지정해 주세요."
    if len(mentions) > 2:
        return None, "여러 날짜를 하나의 연속 기간으로 임의 해석하지 않았습니다. 시작일과 종료일을 지정해 주세요."
    if not mentions:
        if _DATE_WORDS.search(masked):
            return None, "이후·이전의 기준 날짜를 확인하지 못했습니다. 연도와 월 또는 날짜를 지정해 주세요."
        return TrendDateBounds(remainder=masked), None
    start, end = question_date_bounds(masked)
    shortened = _short_range(masked)
    if short_match and any(item[0].start() < short_match.start() or item[0].end() > short_match.end()
                           for item in mentions):
        return None, "축약된 날짜 범위 외에 다른 날짜가 있어 하나의 기간으로 확정하지 못했습니다."
    if len(mentions) == 2 and re.search(r"또는|혹은|\b(?:or|either)\b", masked, re.I):
        return None, "서로 다른 기간의 선택 조건을 하나의 연속 범위로 바꾸지 않았습니다."
    consumed, directions = [], []
    for mention in mentions:
        match = mention[0]
        before, after = _PRE.search(masked[:match.start()]), _POST.search(masked[match.end():])
        words = [found[1].casefold() for found in (before, after) if found]
        if len({_direction(word) for word in words}) > 1:
            return None, "같은 날짜에 이후와 이전 조건이 함께 있어 범위를 확정하지 못했습니다."
        word = words[0] if words else None
        directions.append(word)
        consumed.append((before.start() if before else match.start(),
                         match.end() + after.end() if after else match.end()))
    if shortened is not None:
        if start > end:
            return None, "요청한 날짜 범위가 올바르지 않습니다."
    elif len(mentions) == 1:
        word = directions[0]
        if word:
            start, end = _one_bound(mentions[0], word)
    elif _direction(directions[0]) == "end" or _direction(directions[1]) == "start":
        return None, "두 날짜의 시작·종료 조건이 충돌합니다. 시작일부터 종료일까지로 지정해 주세요."
    else:
        connector = masked[mentions[0][0].end():mentions[1][0].start()]
        if not any(directions) and not re.search(r"[~〜–—-]|사이|\b(?:to|through|until)\b", connector, re.I) \
                and not re.search(r"\bbetween\b", masked[:mentions[0][0].start()], re.I):
            return None, "두 날짜가 연속 범위인지 별도 시점인지 모호합니다. 시작일부터 종료일까지로 지정해 주세요."
        if directions[0] == "after":
            start = _date(mentions[0], True) + timedelta(days=1)
        if directions[1] == "before":
            end = _date(mentions[1], False) - timedelta(days=1)
    if start and end and start > end:
        return None, "요청한 날짜 범위의 시작이 종료보다 늦습니다."
    if shortened is not None:
        remainder = KOREAN_RANGE.sub(" ", ENGLISH_RANGE.sub(" ", masked))
        consumed = []
    else:
        remainder = masked
    for left, right in sorted(consumed, reverse=True):
        remainder = remainder[:left] + " " + remainder[right:]
    if _DATE_WORDS.search(remainder):
        return None, "날짜 조건이 서로 겹치거나 기준이 모호합니다. 날짜 범위를 하나로 지정해 주세요."
    remainder = re.sub(r"\b(?:to|through|until)\b|사이", " ", remainder, flags=re.I)
    note = (calendar_note + f"조회 날짜 범위: {start.date().isoformat() if start else '원본 시작'} ~ "
            f"{end.date().isoformat() if end else '원본 끝'}(경계 포함).")
    return TrendDateBounds(start, end, note, False, remainder), None


def select_trend_periods(observations, bounds):
    return tuple(item for item in observations
                 if (bounds.start is None or item.period.date() >= bounds.start.date())
                 and (bounds.end is None or item.period.date() <= bounds.end.date()))


def _direction(word):
    if word in {"이후", "부터", "에서", "from", "since", "after"}:
        return "start"
    return "end" if word in {"이전", "까지", "으로", "로", "through", "until", "before"} else None


def _one_bound(mention, word):
    if word == "after":
        return _date(mention, True) + timedelta(days=1), None
    if word == "before":
        return None, _date(mention, False) - timedelta(days=1)
    if _direction(word) == "start":
        return _date(mention, False), None
    return None, _date(mention, True)
