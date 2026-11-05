"""Year columns a rule changes must cover every year the request names.

On a table whose header names years (Indicator, 1997, 1998, …) a request such as
"2020년부터 2024년까지 … 모두 5%로" changes one column per year. A reading that
leaves one of those years out would change only part of what was asked, so the
stated years are compared with the year columns the rules change. Only years the
table has as columns count; requests that change no year column, or name no
whole year, are not checked here.
"""
from datetime import date

from app.agent.query.tabular_request_periods import _periods


def unread_years(instruction, headers, offered):
    """Years the request names fully, present as columns, that no rule changes."""
    changed, present = _years(headers), _years(offered)
    if not changed:
        return []
    stated = {year for start, end in _periods(instruction)
              for year in range(start.year, end.year + 1)
              if start <= date(year, 1, 1) and date(year + 1, 1, 1) <= end}
    return [str(year) for year in sorted((stated & present) - changed)]


def _years(headers):
    return {int(header) for header in headers if header.isdigit() and len(header) == 4}
