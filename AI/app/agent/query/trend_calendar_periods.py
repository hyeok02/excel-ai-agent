"""Translate proven quarter/half-year scopes into ordinary date boundaries."""
import re
from datetime import timedelta

from app.agent.query.trend_calendar_tokens import calendar_periods

_PRE = re.compile(r"\b(from|since|after|through|until|before)\s*$", re.I)
_POST = re.compile(r"^\s*(이후|이전|부터|까지)")
_FISCAL = re.compile(r"회계|\bfiscal\b|\bfy(?:\b|(?=\d))", re.I)
_CONNECTOR = re.compile(r"\s*(?:부터|에서)?\s*(?:~|〜|–|—|-|to|through|until|사이|and)?\s*", re.I)
_ONLY_PRE = re.compile(r"\bonly(?:\s+in)?\s*$", re.I)
_ONLY_POST = re.compile(r"^\s*(?:only\b|만)", re.I)


def expand_calendar_periods(text):
    periods, error = calendar_periods(text)
    if error or not periods:
        return text, "", error
    if _FISCAL.search(text):
        return text, "", "원본에 회계 분기·반기의 시작일과 종료일 정의가 없어 달력 기간으로 바꾸지 않았습니다."
    first, last = periods[0], periods[-1]
    before = _PRE.search(text[:first.left])
    after = _POST.search(text[last.right:])
    pre, post = (before[1].casefold() if before else None), (after[1] if after else None)
    start, end = first.start, last.end
    left, right = before.start() if before else first.left, last.right + (after.end() if after else 0)
    if len(periods) == 1:
        if pre and post:
            return text, "", "같은 분기·반기에 여러 시작·종료 조건이 붙어 있습니다."
        direction = pre or post
        if direction in {"after", "before"}:
            start, end = (end + timedelta(days=1), None) if direction == "after" else (None, start - timedelta(days=1))
        elif direction in {"from", "since", "이후", "부터"}:
            end = None
        elif direction in {"until", "through", "이전", "까지"}:
            start = None
    else:
        connector = text[first.right:last.left]
        if not connector.strip() or not _CONNECTOR.fullmatch(connector):
            return text, "", "두 분기·반기가 연속 범위인지 확정하지 못했습니다. 시작 기간부터 종료 기간까지로 지정해 주세요."
        if connector.strip().casefold() == "and" and not re.search(r"\bbetween\s*$", text[:left], re.I):
            return text, "", "별도로 선택한 기간을 하나의 연속 범위로 합치지 않았습니다."
        if pre in {"until", "through", "before"} or post in {"이후", "부터"}:
            return text, "", "분기·반기의 시작·종료 조건이 충돌합니다."
        if pre == "after":
            start = first.end + timedelta(days=1)
    if start and end and start > end:
        return text, "", "분기·반기 범위의 시작이 종료보다 늦습니다."
    if only := _ONLY_PRE.search(text[:left]):
        left = only.start()
    if only := _ONLY_POST.search(text[right:]):
        right += only.end()
    if start is None:
        replacement = f"through {end.date()}"
    elif end is None:
        replacement = f"from {start.date()}"
    else:
        replacement = f"{start.date()} to {end.date()}"
    return text[:left] + " " + replacement + " " + text[right:], "달력 분기·반기 기준입니다. ", None
