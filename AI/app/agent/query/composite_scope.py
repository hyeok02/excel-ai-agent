"""Do not silently guess that a preceding clause's local filters carry over."""
import re
from app.agent.query.boolean_filter_language import parse_boolean
from app.agent.query.tabular_catalog import build_query_tables

_GLOBAL = re.compile(r"전체\s*(?:행|데이터|원본)|모든\s*행|(?:조건|필터)\s*없이|"
                     r"\ball\s+(?:rows?|records?|data)\b|\bunfiltered\b", re.I)


def ambiguous_local_scope(split, position, proposed, previous_answers, sources=None):
    if position == 0 or _GLOBAL.search(split.parts[position]):
        return False
    current = proposed.parts[position] if proposed is not None else None
    current_columns = (_filter_columns(current) if proposed is not None else
                       _source_filter_columns(split.question_for(position), sources))
    for earlier in range(position):
        part = proposed.parts[earlier] if proposed is not None else None
        previous_columns = (_filter_columns(part) if proposed is not None else
                            _source_filter_columns(split.question_for(earlier), sources))
        if previous_columns and not previous_columns <= current_columns:
            return True
        # If original conditions cannot be bound, the checked answer's condition
        # line is reason to abstain, never evidence for copying its values.
        if not previous_columns and not split.shared_prefix and earlier < len(previous_answers):
            answer = previous_answers[earlier]
            if answer.verification.level == "request_checked" and answer.answer.startswith("조건:"):
                return True
    return False


def _filter_columns(part):
    if part is None:
        return set()
    query = part.tabular_query or part.relational_query
    return {condition.column_id for condition in query.filters} if query is not None else set()


def _source_filter_columns(question, sources):
    summary = getattr(sources, "summary", None)
    if summary is None:
        return set()
    tables = build_query_tables(summary)
    if len(tables) > 64:
        return set()
    matches = []
    for table in tables:
        parsed = parse_boolean(question, table)
        if parsed is not None and parsed.filters:
            matches.append({(table.id, condition.column_id) for condition in parsed.filters})
    # Source identity is required; identical column letters across tables do not
    # establish shared scope. The child executor still verifies all predicates.
    return matches[0] if len(matches) == 1 else set()
