"""Apply explicit source coordinates before interpreting metric/entity scope."""
import re

from app.agent.query.tabular_request_scope import explicit_ranges, _inside

_REFERENCE = re.compile(
    r"(?:'([^']+)'|([\w& .-]+))!\$?([A-Za-z]{1,3}\$?[1-9]\d*)"
    r"(?::\$?([A-Za-z]{1,3}\$?[1-9]\d*))?",
)


def bind_explicit_metric_scope(question, observations):
    ranges = explicit_ranges(question)
    if not ranges:
        return observations, question
    if any(not any(sheet == item.value.sheet_name and _inside(item.value.address, reference)
                   for item in observations) for sheet, reference in ranges):
        return [], question
    selected = [item for item in observations if any(sheet == item.value.sheet_name
                and _inside(item.value.address, reference) for sheet, reference in ranges)]
    # Only a successfully bound source coordinate may be consumed. Unknown or
    # contradictory references must not silently disappear from the request.
    if not selected:
        return [], question
    return selected, _REFERENCE.sub(" ", question)
