"""Format source-derived statistics without interpreting category symbols."""
from collections import Counter
from datetime import datetime, time
import json
import re

from app.agent.query.excel_number_formats import display_value, parse_number_format
from app.agent.query.models import QuestionAnswerEvidence
from app.agent.query.tabular_numeric import numeric_summary
from app.services.provenance import EvidenceKind

MAX_DISPLAY_CATEGORIES = 30


def aggregate_text(operation, columns, rows, statistic="all"):
    if operation == "row_count":
        return f"조건에 해당하는 행은 {len(rows)}건입니다.", []
    if operation in {"lookup", "row_list"}:
        if operation == "lookup" and len(rows) != 1:
            return None, []
        if not rows:
            return "지정한 조건에 맞는 행이 없습니다.", []
        lines = []
        for row in rows[:50]:
            parts = []
            for column in columns:
                value = row.values[column.id]
                if value is None and row.formulas.get(column.id):
                    return None, []
                text = _display_cell(value, row.number_formats.get(column.id, "General"))
                parts.append(f"{column.display_header}: {text}")
            lines.append("; ".join(parts))
        limitations = ([f"해당하는 {len(rows)}개 행 중 앞의 50개 행만 표시했습니다."]
                       if len(rows) > 50 else [])
        return "\n".join(lines), limitations
    lines, limitations = [], []
    for column in columns:
        values = [row.values[column.id] for row in rows]
        if operation == "frequencies":
            result, limited = _frequencies(values)
        elif operation == "numeric_summary":
            formats = [row.number_formats.get(column.id, "General") for row in rows]
            result, limited = numeric_summary(values, formats, statistic)
            if result is None:
                return None, []
        else:
            return None, []
        lines.append(f"‘{column.display_header}’: {result}.")
        limitations.extend(limited)
    return "\n".join(lines), list(dict.fromkeys(limitations))


def _display_cell(value, number_format):
    if value in (None, ""):
        return "빈칸"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return display_value(value, parse_number_format(number_format))
    return str(value)


def scope_description(plan, table):
    columns = {column.id: column.display_header for column in table.columns}
    operators = {"equals": "=", "not_equals": "≠", "contains": "포함",
                 "is_blank": "빈칸", "not_blank": "비어 있지 않음",
                 "greater_than": ">", "greater_than_or_equal": "≥",
                 "less_than": "<", "less_than_or_equal": "≤"}
    parts = []
    for condition in plan.filters:
        value = "" if condition.operator in {"is_blank", "not_blank"} else str(condition.value)
        if getattr(plan, "filter_expression", None) is not None and isinstance(condition.value, str):
            value = json.dumps(condition.value, ensure_ascii=False)
        if condition.value_unit == "percent":
            value += "%"
        parts.append(f"{columns[condition.column_id]} {operators[condition.operator]} {value}".strip())
    if getattr(plan, "filter_expression", None) is not None:
        from app.agent.query.boolean_filters import render_expression
        parts = [render_expression(plan.filter_expression, parts)]
    if plan.order_by:
        parts.append(f"{columns[plan.order_by]} {'내림차순' if plan.descending else '오름차순'}")
    if plan.limit:
        parts.append(f"앞의 {plan.limit}개 행")
    return "조건: " + ", ".join(parts) + "\n" if parts else ""


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
    # A date cell with no time of day reads as the date the source shows.
    if isinstance(value, datetime) and value.time() == time.min:
        return value.date().isoformat()
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T00:00:00", value):
        return value[:10]
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
            reference=f"{first}:{last}", label=column.display_header,
            description=f"원본 열 {len(table.rows)}개 행을 대조해 조건에 맞는 {len(rows)}개 행을 집계",
        ))
        evidence.extend(QuestionAnswerEvidence(
            kind=EvidenceKind.CELL, sheet_name=table.sheet_name,
            reference=reference.rpartition("!")[2], label=label, value=label,
            description="요청한 항목을 구분하는 원본 상위 머리글",
        ) for reference, label in column.header_path)
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
