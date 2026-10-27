"""Resolve source header mentions without detaching repeated leaves from parents."""
import re

from app.agent.query.tabular_request_literals import source_headers

_TOTAL = re.compile(r"계|합계|총계|총합계|총합|전체|total|grand\s+total|all", re.I)


def bound_header_mentions(text, table):
    """An ancestor alone selects its unique total leaf, never an arbitrary child.

    These are exact labels read from the workbook, not translated business
    aliases. Ambiguous bare leaves and nested parents remain unbound.
    """
    candidates = list(source_headers(text, table))
    for column in table.columns:
        if not column.header_path:
            continue
        labels = {column.display_header}
        for _, parent in column.header_path:
            family = [item for item in table.columns
                      if parent in {label for _, label in item.header_path}]
            totals = [item for item in family if _TOTAL.fullmatch(item.header.strip())]
            if len(totals) == 1 and totals[0].id == column.id:
                labels.add(parent)
        for label in labels:
            candidates.extend((column.id, match) for match in re.finditer(
                r"(?<![\w])" + re.escape(label) + r"(?![A-Za-z0-9_])", text, re.I))
    candidates = [(column, match) for column, match in candidates
                  if not any(other.start() <= match.start() and other.end() >= match.end()
                             and other.end() - other.start() > match.end() - match.start()
                             for _, other in candidates)]
    owners = {}
    for column, match in candidates:
        owners.setdefault(match.span(), set()).add(column)
    seen = set()
    unique = []
    for column, match in candidates:
        key = column, match.span()
        if len(owners[match.span()]) == 1 and key not in seen:
            unique.append((column, match))
            seen.add(key)
    return unique
