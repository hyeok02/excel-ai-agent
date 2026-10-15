"""Keep a reporting period's date, grain and scenario together.

A shared end date does not make an annual, quarterly and trailing-year amount
interchangeable. These types carry the original qualifiers through selection.
"""

import re
from dataclasses import dataclass
from datetime import datetime

from app.agent.query.question_date_mentions import calendar_mentions

GRAINS = {
    "annual": re.compile(r"회계연도|연간|연도별|\b(?:annual|fiscal\s+year|fy)(?:\b|(?=\d))", re.I),
    "quarter": re.compile(r"분기|\bquarter(?:ly)?\b|\bfq\b|\bq[1-4]\b", re.I),
    "month": re.compile(r"월간|월별|\bmonthly\b", re.I),
    "ltm": re.compile(r"최근\s*12\s*개월|\b(?:ltm|ttm|last\s+twelve\s+months)\b", re.I),
}
SCENARIOS = {
    "actual": re.compile(r"실제|실적|\bactuals?\b", re.I),
    "estimate": re.compile(r"예상|추정|전망|예측|\b(?:estimates?|forecast|consensus|projected)\b", re.I),
    "budget": re.compile(r"예산|\bbudget\b", re.I),
}
LATEST = re.compile(r"최신|최근|현재|마지막|\b(?:latest|most\s+recent|current|last)\b", re.I)


@dataclass(frozen=True)
class PeriodRequest:
    year: int
    month: int | None = None
    day: int | None = None
    grain: str | None = None
    scenario: str | None = None

    def matches(self, period: datetime, grain: str | None, scenario: str | None) -> bool:
        return (
            period.year == self.year
            and (self.month is None or period.month == self.month)
            and (self.day is None or period.day == self.day)
            and (self.grain is None or grain == self.grain)
            and (self.scenario is None or scenario == self.scenario)
        )


def source_period(value: object) -> datetime | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return datetime(int(value), 1, 1) if value == int(value) and 1900 <= value <= 2100 else None
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.strip()).replace(tzinfo=None)
    except ValueError:
        match = re.fullmatch(r"(?:FY\s*)?((?:19|20)\d{2})(?:\s*[AE])?", value.strip(), re.I)
        return datetime(int(match[1]), 1, 1) if match else None


def qualifier(value: object, patterns: dict[str, re.Pattern]) -> str | None:
    if not isinstance(value, str):
        return None
    found = [name for name, pattern in patterns.items() if pattern.search(value)]
    return found[0] if len(found) == 1 else None


def requested_periods(question: str) -> list[PeriodRequest]:
    mentions = calendar_mentions(question)
    if not mentions:
        return []
    grains = _qualifiers(question, GRAINS)
    scenarios = _qualifiers(question, SCENARIOS)
    result = []
    for index, mention in enumerate(mentions):
        _, _, year, month, day = mention
        result.append(PeriodRequest(
            year, month, day,
            _local_qualifier(mention, index, mentions, grains),
            _local_qualifier(mention, index, mentions, scenarios),
        ))
    # "FY and quarter ending on ..." has one date and two different periods.
    if len(result) == 1:
        base = result[0]
        kinds = list(dict.fromkeys(name for _, _, name in grains))
        cases = list(dict.fromkeys(name for _, _, name in scenarios))
        if len(kinds) > 1 and len(cases) <= 1:
            return [PeriodRequest(base.year, base.month, base.day, kind, base.scenario)
                    for kind in kinds]
        if len(cases) > 1 and len(kinds) <= 1:
            return [PeriodRequest(base.year, base.month, base.day, base.grain, case)
                    for case in cases]
    return result


def _qualifiers(question, patterns):
    return sorted((match.start(), match.end(), name)
                  for name, pattern in patterns.items()
                  for match in pattern.finditer(question))


def _local_qualifier(mention, index, mentions, values):
    unique = {name for _, _, name in values}
    if len(unique) == 1:
        return next(iter(unique))
    if not values:
        return None
    # A qualifier can precede or follow its date. Assign it to the nearest
    # calendar mention first, so "actual 2025 / forecast 2026" cannot borrow
    # the following period's scenario for the first value.
    def distance(value, date):
        return max(date[0] - value[1], value[0] - date[1], 0)

    local = [value for value in values
             if distance(value, mention) == min(distance(value, date) for date in mentions)]
    nearest = sorted(local, key=lambda value: distance(value, mention))
    if not nearest:
        return None
    closest = {name for start, end, name in nearest
               if distance((start, end, name), mention) == distance(nearest[0], mention)}
    return next(iter(closest)) if len(closest) == 1 else None
