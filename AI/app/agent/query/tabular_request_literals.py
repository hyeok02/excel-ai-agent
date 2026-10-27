"""Keep quoted source values separate from request grammar."""
import re
from app.agent.query.tabular_request_predicates import _PREFIX

_LITERAL = re.compile(r"'[^']*'|\"[^\"]*\"|‘[^’]*’|“[^”]*”")


def without_literals(text):
    return _LITERAL.sub(lambda match: " " * len(match.group()), text)


def source_headers(text, table):
    literals = list(_LITERAL.finditer(text))
    spans = [(match.start(), match.end()) for match in literals]
    headers = [(column.id, match) for column in table.columns
               for match in re.finditer(r"(?<![\w])" + re.escape(column.header) + r"(?![A-Za-z0-9_])", text, re.I)
               if not any(start <= match.start() < end for start, end in spans)]
    # Users also quote column names. A complete quoted header followed by a
    # predicate operator remains a field, not a value inside another field.
    headers.extend((column.id, match) for column in table.columns for match in literals
                   if match.group()[1:-1].casefold() == column.header.casefold()
                   and _predicate_follows(text[match.end():]))
    return [(column, match) for column, match in headers
            if not any(other.start() <= match.start() and other.end() >= match.end()
                       and other.end() - other.start() > match.end() - match.start()
                       for _, other in headers)]


def _predicate_follows(text):
    match = _PREFIX.match(text)
    return bool(re.match(r"\s*(?:>=|<=|≥|≤|>|<)\s*[-+]?\d", text)
                or (match and (match.group("operator") or match.group("body") != text.lstrip())))
