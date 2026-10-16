"""Keep a source-selected column for a bounded aggregation-only follow-up."""
import re
from openpyxl.utils.cell import quote_sheetname

from app.agent.query.conversation_models import ContextResolutionDraft
from app.agent.query.tabular_catalog import build_query_tables

_OPERATIONS = {
    "합계": r"합계|총합|\bsum\b|\btotal\b",
    "평균": r"평균|\baverage\b|\bmean\b",
    "최대": r"최대(?:값)?|\bmaximum\b|\bhighest\b|\bmax\b",
    "최소": r"최소(?:값)?|\bminimum\b|\blowest\b|\bmin\b",
}
_GRAMMAR = re.compile(r"(?:그럼|그러면|그렇다면|그|이|해당|같은|항목|열|값|기준|은|는|의|을|를|도|만|로|으로|"
                      r"알려줘|알려주세요|보여줘|보여주세요|구해줘|얼마야|얼마|야|좀|\s|[?？.!])+|"
                      r"\b(?:then|and|the|same|that|this|column|field|value|its|it|what|is|please|show|tell|me|of)\b", re.I)


def bound_choice_operation(question, context, entries, summary):
    if not context.turns or context.turns[-1].needs_clarification:
        return None
    latest = f"turn:{len(context.turns) - 1}"
    if not any(entry["id"] == latest for entry in entries):
        return None
    requested = [label for label, pattern in _OPERATIONS.items() if re.search(pattern, question, re.I)]
    if len(requested) != 1:
        return None
    remainder = re.sub(_OPERATIONS[requested[0]], "", question, flags=re.I)
    if _GRAMMAR.sub("", remainder).strip():
        return None
    previous = context.turns[-1].question
    for table in build_query_tables(summary):
        for column in table.columns:
            if column.id in table.hidden_columns:
                continue
            prefix = f"{quote_sheetname(table.sheet_name)}!{table.reference} 범위의 {column.id}열 {column.header} 기준으로: "
            if not previous.startswith(prefix):
                continue
            operation = previous[len(prefix):]
            updated = _replace_operation(operation, requested[0], table)
            if updated is None or len(prefix + updated) > 1000:
                return None
            return ContextResolutionDraft(status="resolved", question=prefix + updated, context_ids=[latest])
    return None


def _replace_operation(question, requested, table):
    # Labels such as "Total Revenue" and record IDs such as "Sum Fund" are
    # source text, not aggregation commands that may be rewritten.
    labels = {column.header for column in table.columns}
    labels.update(value for row in table.rows for value in row.values.values() if isinstance(value, str))
    protected = [match.span() for label in labels if label.strip()
                 for match in re.finditer(re.escape(label), question, re.I)]
    matches = [match for pattern in _OPERATIONS.values() for match in re.finditer(pattern, question, re.I)
               if not any(start <= match.start() and match.end() <= end for start, end in protected)]
    if len(matches) != 1:
        return None
    match = matches[0]
    return question[:match.start()] + requested + question[match.end():]
