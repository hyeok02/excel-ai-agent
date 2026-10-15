"""Public calendar spans used to bind local reporting-period qualifiers."""

from app.agent.query.question_dates import _mentions


def calendar_mentions(query: str) -> list[tuple[int, int, int, int | None, int | None]]:
    mentions, invalid = _mentions(query)
    if invalid:
        return []
    return [(match.start(), match.end(), year, month, day)
            for match, year, month, day in mentions]
