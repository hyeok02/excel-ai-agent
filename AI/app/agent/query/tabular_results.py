"""Format source-derived statistics without interpreting category symbols."""
from collections import Counter

from app.agent.query.models import QuestionAnswerEvidence
from app.agent.query.tabular_numeric import numeric_summary
from app.services.provenance import EvidenceKind

MAX_DISPLAY_CATEGORIES = 30


def aggregate_text(operation, columns, rows):
    if operation == "row_count":
        return f"조건에 해당하는 행은 {len(rows)}건입니다.", []
    lines, limitations = [], []
    for column in columns:
        values = [row.values[column.id] for row in rows]
        if operation == "frequencies":
            result, limited = _frequencies(values)
        elif operation == "numeric_summary":
            formats = [row.number_formats.get(column.id, "General") for row in rows]
            result, limited = numeric_summary(values, formats)
            if result is None:
                return None, []
        else:
            return None, []
        lines.append(f"‘{column.header}’: {result}.")
        limitations.extend(limited)
    return "\n".join(lines), list(dict.fromkeys(limitations))


def _frequencies(values):
    counts = Counter((type(value).__name__, value) for value in values if value not in (None, ""))
    entries = list(counts.items())
    parts = [f"‘{_label(value)}’ {count}건" for (_, value), count in entries[:MAX_DISPLAY_CATEGORIES]]
    parts.append(f"빈칸 {sum(value in (None, '') for value in values)}건")
    limitations = []
    if len(entries) > MAX_DISPLAY_CATEGORIES:
        remaining = sum(count for _, count in entries[MAX_DISPLAY_CATEGORIES:])
        parts.append(f"그 외 {len(entries) - MAX_DISPLAY_CATEGORIES}종 {remaining}건")
        limitations.append("값 종류가 많아 일부 항목은 나머지 건수로 묶어 표시했습니다.")
    return ", ".join(parts) + f" (총 {len(values)}건)", limitations


def _label(value):
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    return str(value)


def query_evidence(table, needed, rows, include_identity):
    columns = {column.id: column for column in table.columns}
    if include_identity:
        identity = _identity_column(table)
        if identity is not None:
            needed = needed | {identity}
    evidence = []
    for column_id in columns:
        if column_id not in needed:
            continue
        column = columns[column_id]
        first = column.header_reference.rpartition("!")[2]
        last = f"{column_id}{table.rows[-1].row_number}"
        evidence.append(QuestionAnswerEvidence(
            kind=EvidenceKind.RANGE, sheet_name=table.sheet_name,
            reference=f"{first}:{last}", label=column.header,
            description=f"원본 열 {len(table.rows)}개 행을 대조해 조건에 맞는 {len(rows)}개 행을 집계",
        ))
    if not evidence:
        evidence.append(QuestionAnswerEvidence(
            kind=EvidenceKind.RANGE, sheet_name=table.sheet_name,
            reference=table.reference, label="집계 대상 표",
            description=f"원본 표의 {len(table.rows)}개 행을 대조해 {len(rows)}개 행을 집계",
        ))
    return evidence


def _identity_column(table):
    for column in table.columns:
        values = [row.values[column.id] for row in table.rows]
        keys = {(type(value).__name__, str(value)) for value in values}
        if all(value not in (None, "") for value in values) and len(keys) == len(values):
            return column.id
    return None
