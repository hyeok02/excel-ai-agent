"""Bind relative calendar periods to source-corroborated prior question dates."""
import calendar
import re
from datetime import date

from app.agent.query.conversation_language import standalone_wording

RELATIVE_YEAR = re.compile(r"전년도|전년|작년|지난해|전해|다음년도|다음해|내년|"
                           r"\b(?:previous|prior|last|next)\s+year\b", re.I)
_DATE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?:년\s*|[-/])(\d{1,2})(?:월\s*|[-/])(\d{1,2})일?")


def _dates(text):
    found = set()
    for match in _DATE.finditer(str(text)):
        try:
            found.add(date(*map(int, match.groups())))
        except ValueError:
            pass
    return found


def bound_relative_question(question: str, entries: list[dict]) -> str | None:
    """Return a deterministic rewrite only when one cited prior date anchors it."""
    relative = RELATIVE_YEAR.search(question)
    if relative is None:
        return None
    turns = [entry for entry in entries if entry["id"].startswith("turn:")]
    if not turns:
        return None
    latest = max(turns, key=lambda entry: int(entry["id"].split(":")[1]))
    stated = _dates(latest.get("hint", {}).get("question", ""))
    source = {value for cell in latest["source_cells"] for value in _dates(cell["value"])}
    anchors = stated & source
    if len(anchors) != 1:
        return None
    anchor = anchors.pop()
    forward = re.search(r"다음|내년|next", relative.group(), re.I)
    year = anchor.year + (1 if forward else -1)
    day = min(anchor.day, calendar.monthrange(year, anchor.month)[1])
    replacement = f"{year}년 {anchor.month}월 {day}일"
    rewritten = RELATIVE_YEAR.sub(replacement, standalone_wording(question))
    rewritten = re.sub(r"같은\s*(분기|회계연도|연도)|same\s+(quarter|fiscal year|year)",
                       lambda match: match.group(1) or match.group(2), rewritten, flags=re.I)
    sheets = {cell["reference"].rsplit("!", 1)[0].strip("'") for cell in latest["source_cells"]}
    if len(sheets) == 1 and (sheet := next(iter(sheets))) not in rewritten:
        rewritten = f"{sheet} 시트에서 {rewritten}"
    return rewritten
