"""Table choices show grounded examples instead of address-only metadata."""
import re
from openpyxl.utils.cell import quote_sheetname

from app.agent.query.ambiguity_candidates import AmbiguousCandidate
from app.agent.query.clarification_preview_scope import absent_source_value, unrequested_detail_population
from app.agent.query.clarification_preview_values import latest_preview_rows, preview_row
from app.agent.query.metric_observation_cells import _DATE_HEADER, _numeric
from app.agent.query.source_record_identity import requested_record_rows

_SNAPSHOT = re.compile(r"\b(?:latest|current|most\s+recent)\b|현재|최신", re.I)


def table_choice(question, table, column, cells, index):
    complete = table.complete and not index.truncated_for({table.sheet_name})
    rows = [row for row in table.rows if row.row_number not in table.excluded_rows]
    complete = complete and _source_rows_match(table, rows, cells)
    if unrequested_detail_population(question, table, complete):
        return None
    selected, period_note = latest_preview_rows(question, table, column, rows, complete)
    selected = requested_record_rows(table, question, selected)
    if complete and selected and all(absent_source_value(row.values.get(column.id)) for row in selected):
        return None
    header = cells.get(column.header_reference)
    references = [header] if header else []
    previews = []
    for row in selected:
        if absent_source_value(row.values.get(column.id)):
            continue
        preview = preview_row(table, column, row, cells, index.rows)
        if preview is not None:
            previews.append(preview)
            references.extend(preview[1])
        if len(previews) == 3:
            break
    context = " / ".join(dict.fromkeys(text for _, text in table.context))[-160:]
    formats = ", ".join(value for value in column.number_formats if value != "General")
    parts = [period_note] if period_note else []
    parts += ["원본 값 예시 (집계 결과 아님):\n" + "\n".join(item[0] for item in previews)] if previews else ["원본 값 미확인"]
    missing = sum(absent_source_value(row.values.get(column.id)) for row in selected)
    if missing:
        parts.append(f"선택 범위의 {missing}개 행은 저장값 미확인")
    if not previews or not any(item[2] for item in previews):
        parts.append("기준일 미확인")
    if not previews or not all(item[3] for item in previews):
        parts.append("단위 미확인")
    if formats:
        parts.append(f"표시 형식: {formats}")
    if context:
        parts.append(context)
    scope = f"{quote_sheetname(table.sheet_name)}!{table.reference}"
    candidate = AmbiguousCandidate(column.header, scope, "\n".join(parts),
        f"{scope} 범위의 {column.id}열 {column.header} 기준으로: {question}",
        tuple(dict.fromkeys(references)))
    dated = any(_DATE_HEADER.search(item.header) for item in table.columns if item.id not in table.hidden_columns)
    stored = bool(selected) and all(_numeric(row.values.get(column.id)) for row in selected)
    available = bool(previews) and complete and stored and (
        dated and not period_note or not dated and bool(_SNAPSHOT.search(column.header)))
    return candidate, available, dated and not available


def _source_rows_match(table, rows, cells):
    for row in rows:
        for key, value in row.values.items():
            source = cells.get(f"{table.sheet_name}!{key}{row.row_number}")
            actual = source.value if source else None
            if actual != value and not (absent_source_value(actual) and absent_source_value(value)):
                return False
    return True
