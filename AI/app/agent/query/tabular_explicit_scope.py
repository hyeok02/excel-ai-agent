"""Parse and enforce user-specified source coordinates independently of plans."""
import re

from openpyxl.utils import range_boundaries


def explicit_ranges(question, *, include_unqualified=False):
    qualified = list(re.finditer(
        r"(?:'((?:[^']|'')+)'|([\w& .-]+))!\$?([A-Za-z]{1,3}\$?[1-9]\d*)(?::\$?([A-Za-z]{1,3}\$?[1-9]\d*))?",
        question))
    ranges = [(match[1].replace("''", "'") if match[1] else match[2],
               match[3].upper() + (":" + match[4].upper() if match[4] else "")) for match in qualified]
    if not include_unqualified:
        return ranges
    # An unqualified *range* is still a bound. A lone A12 could be a record ID,
    # so keep the existing ID-as-filter rule for standalone unqualified cells.
    for match in re.finditer(r"(?<![\w!])\$?([A-Za-z]{1,3}\$?[1-9]\d*)\s*:\s*"
                             r"\$?([A-Za-z]{1,3}\$?[1-9]\d*)(?![A-Za-z0-9_])", question):
        if not any(item.start() <= match.start() < item.end() for item in qualified):
            ranges.append(("", match[1].upper() + ":" + match[2].upper()))
    return ranges


def rows_match_explicit_ranges(question, table, columns, rows):
    for _, reference in explicit_ranges(question, include_unqualified=True):
        for row in rows:
            for column in columns:
                if not _inside(f"{column}{row.row_number}", reference):
                    return False
    return True


def _inside(inner, outer):
    a, b, c, d = range_boundaries(inner.replace("$", ""))
    e, f, g, h = range_boundaries(outer.replace("$", ""))
    return e <= a <= c <= g and f <= b <= d <= h


_FOLLOW_UP = re.compile(r"^\s*(?:'(?:[^']|'')+'|[\w& .-]+)![A-Z$]+\d+(?::[A-Z$]+\d+)?\s*범위(?:의|에서)?[^:\n]*?기준으로:\s*")


def asked_part(question):
    """A clarification's follow-up ("'Sheet'!B13:AL74 범위의 J열 X 기준으로: 질문") without its scope prefix."""
    return _FOLLOW_UP.sub("", question)
