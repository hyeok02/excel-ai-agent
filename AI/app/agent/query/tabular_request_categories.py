"""Bind repeated categorical values to the source field named in the request."""
import re
from app.agent.query.tabular_request_predicates import (
    categorical_predicates, local_operator, predicates_match,
)
from app.agent.query.tabular_request_literals import source_headers

_BRIDGE = re.compile(
    r"[\s:'\"‘’“”=]*(?:(?:이|가|은|는|의|을|를|에|값|표시|상태|인|아닌|제외|포함된|포함한|포함)|"
    r"(?:is|are|equals?|not|contains?|value|status)\b|[\s:'\"‘’“”=])*", re.I,
)


def categories_match(text, plan, table):
    headers = source_headers(text, table)
    if not predicates_match(categorical_predicates(text, headers), plan):
        return False
    for condition in plan.filters:
        if not isinstance(condition.value, str):
            continue
        named = {column for match in value_matches(text, condition.value)
                 for column in _adjacent_headers(text, match.start(), match.end(), headers)}
        if named and condition.column_id not in named:
            return False
    matches = []
    header_names = {_normal(column.header) for column in table.columns}
    for column in table.columns:
        values = {value for row in table.rows
                  if isinstance(value := row.values[column.id], str) and value.strip()}
        for value in values:
            if _normal(value) in header_names:
                continue
            for match in value_matches(text, value):
                if not any(header.start() <= match.start() and header.end() >= match.end()
                           for _, header in headers):
                    matches.append((column.id, value, match))
    # A source key such as "Unit #21" owns its entire span, not a shorter value
    # or an ID fragment that also happens to occur in another column.
    matches = [(column, value, match) for column, value, match in matches
               if not any(other.start() <= match.start() and other.end() >= match.end()
                          and len(other_value) > len(value)
                          for _, other_value, other in matches)]
    groups = {}
    for column, value, match in matches:
        groups.setdefault((match.start(), match.end(), _normal(value)), set()).add(column)
    supported = set()
    for (start, end, value), columns in groups.items():
        named = _adjacent_headers(text, start, end, headers)
        if not named and re.fullmatch(r"[?!.,:;]+", value):
            # Workbook markers such as '?' also occur as ordinary sentence
            # punctuation. Only an explicit field binding makes them a filter.
            continue
        if named:
            columns = columns & named
        # Shared x/o/status values do not authorize guessing which field the
        # user meant, nor filtering every field that happens to contain them.
        if len(columns) != 1:
            return False
        column = next(iter(columns))
        operator = local_operator(text, start, end, headers)
        binding = (column, value, operator)
        if not any((condition.column_id, _normal(condition.value), condition.operator) == binding
                   for condition in plan.filters if isinstance(condition.value, str)):
            return False
        supported.add(binding)
    stated_values = {value for _, _, value in groups}
    return all(not isinstance(condition.value, str) or _normal(condition.value) not in stated_values
               or (condition.column_id, _normal(condition.value), condition.operator) in supported
               for condition in plan.filters)


def _adjacent_headers(text, start, end, headers):
    candidates = []
    for column, header in headers:
        if header.end() <= start:
            gap = text[header.end():start]
        else:
            continue
        if len(gap) <= 40 and _BRIDGE.fullmatch(gap):
            candidates.append((len(gap), column))
    nearest = min((distance for distance, _ in candidates), default=None)
    return {column for distance, column in candidates if distance == nearest}


def value_matches(text, value):
    normalized = str(value).strip()
    if len(normalized) > 300 or re.fullmatch(r"[-+]?\d[\d,./:% -]*", normalized):
        return []
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(normalized)}(?![A-Za-z0-9_])"
    if re.fullmatch(r"[가-힣]+", normalized):
        pattern = rf"(?<![가-힣]){re.escape(normalized)}(?=$|\s|[,.?!'\"]|인|이|가|은|는|을|를|의|와|과|만|에|아닌|제외)"
    return list(re.finditer(pattern, text, re.I))


def _normal(value):
    return " ".join(str(value).casefold().split())
