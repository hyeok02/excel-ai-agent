"""Bind relative-rank phrases to one exact source identity; never infer aliases."""
import re

from app.agent.query.tabular_request_categories import value_matches, _adjacent_headers
from app.agent.query.tabular_request_literals import source_headers

_RELATIVE = re.compile(r"다음(?:으로)?\s*(?:순위)?|이전\s*순위|직전\s*순위|"
                       r"\b(?:after|before|next\s+rank|previous\s+rank)\b", re.I)


def relative_request_text(text, plan, table):
    anchor = getattr(plan, "relative_rank", None)
    if anchor is None:
        from app.agent.query.tabular_request_literals import without_literals
        ranked = bool(getattr(plan, "order_by", None) or getattr(plan, "limit", None)
                      or re.search(r"순위|가장|제일|\b(?:rank|highest|lowest)\b", text, re.I))
        return None if ranked and _RELATIVE.search(_grammar(without_literals(text), table)) else text
    from app.agent.query.relative_group_ranking import relative_plan_valid
    if not relative_plan_valid(plan) or anchor.column_id not in {column.id for column in table.columns}:
        return None
    value = str(anchor.value)
    if not isinstance(anchor.value, str):
        expression = r"(?<![\w.])" + re.escape(value) + r"(?![\w.])"
        matches = list(re.finditer(expression, text, re.I))
    else:
        matches = value_matches(text, value)
    spans = []
    for match in matches:
        named = _adjacent_headers(text, match.start(), match.end(), source_headers(text, table))
        if named and anchor.column_id not in named:
            continue
        tail = re.match(r"\s*['’”\"]?\s*(?:의\s*)?(?P<direction>다음(?:으로)?|이전(?:으로)?|직전)"
                        r"\s*(?:순위)?", text[match.end():])
        prefix = re.search(r"\b(?P<direction>after|before)\s*['‘“\"]?\s*$", text[:match.start()], re.I)
        if tail:
            direction = "after" if tail.group("direction").startswith("다음") else "before"
            spans.append((match.start(), match.end() + tail.end(), direction))
        elif prefix:
            spans.append((prefix.start(), match.end(), "after" if prefix.group("direction").lower() == "after" else "before"))
    if len(spans) != 1 or spans[0][2] != anchor.direction:
        return None
    start, end, _ = spans[0]
    # Remove a matching surrounding quote along with the independently bound anchor.
    if start and text[start - 1] in "'‘“\"":
        start -= 1
    if end < len(text) and text[end] in "'’”\"":
        end += 1
    remainder = text[:start] + " " * (end - start) + text[end:]
    return None if _RELATIVE.search(_grammar(remainder, table)) else remainder


def _grammar(text, table):
    from app.agent.query.source_measure_labels import bound_header_mentions
    spans = [match.span() for _, match in bound_header_mentions(text, table)]
    labels = {table.sheet_name, *(str(value) for column in table.columns
                                 for _, value in getattr(column, "source_identifiers", ()))}
    for label in labels:
        if label:
            spans.extend(match.span() for match in re.finditer(
                r"(?<![\w])" + re.escape(label) + r"(?![A-Za-z0-9_])", text, re.I))
    for start, end in sorted(set(spans), reverse=True):
        text = text[:start] + " " * (end - start) + text[end:]
    return text
