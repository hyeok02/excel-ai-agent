"""Render deterministic join values and exact original-cell evidence."""
from collections import defaultdict

from app.agent.query.models import QuestionAnswerEvidence
from app.agent.query.relational_models import RelationalError
from app.agent.query.tabular_results import _display_cell
from app.agent.query.tabular_numeric import numeric_summary
from app.services.provenance import EvidenceKind


def relational_text(plan, sides, joined, unmatched, population):
    scope = (f"연결 기준: {_key_description(plan, sides)}\n"
             f"왼쪽 표 {population}개 행 중 연결 성공 {population - unmatched}개, 연결 안 됨 {unmatched}개.\n")
    if plan.population == "matched_only":
        scope += "요청에 따라 연결된 행만 포함했습니다.\n"
    if plan.operation == "row_count":
        if plan.group_by:
            return scope + _aggregate(plan, sides, joined), []
        return scope + f"결과는 왼쪽 원본 행 기준 {len(joined)}건입니다.", []
    if not plan.column_ids:
        raise RelationalError("답변할 원본 열이 선택되지 않았습니다.")
    if plan.operation == "lookup" and len(joined) != 1:
        raise RelationalError(f"조건에 맞는 연결 행이 {len(joined)}개여서 단일 값을 확정하지 못했습니다.")
    if plan.operation == "numeric_summary":
        return scope + _aggregate(plan, sides, joined), []
    lines = []
    for item in joined[:50]:
        values = []
        for reference in plan.column_ids:
            value, style, row = _value(item, reference)
            rendered = "연결 안 됨 (값 없음)" if row is None else _display_cell(value, style)
            values.append(f"{_label(reference, sides)}: {rendered}")
        lines.append("; ".join(values))
    limits = [f"결과 {len(joined)}개 중 처음 50개 행만 표시했습니다."] if len(joined) > 50 else []
    return scope + ("\n".join(lines) or "조건에 맞는 연결 행이 없습니다."), limits


def _aggregate(plan, sides, joined):
    if not joined:
        return "조건에 맞는 행이 없어 집계할 값이 없습니다. 빈 집합을 0으로 대신하지 않았습니다."
    if plan.operation == "numeric_summary" and any(ref.startswith("right.") for ref in plan.column_ids):
        right_rows = [item.right.row_number for item in joined if item.right is not None]
        if len(right_rows) != len(set(right_rows)):
            raise RelationalError("같은 오른쪽 행이 여러 번 연결되어 해당 값의 중복 집계를 막았습니다.")
    groups = defaultdict(list)
    for item in joined:
        keys = []
        for reference in plan.group_by:
            value, style, row = _value(item, reference)
            if row is None or value in (None, ""):
                raise RelationalError("그룹을 결정할 연결 값이 누락되어 일부 행을 제외한 합계를 만들지 않았습니다.")
            keys.append((type(value).__name__, value, _display_cell(value, style)))
        groups[tuple(keys)].append(item)
    if len(groups) > 100:
        raise RelationalError("그룹이 100개를 초과합니다. 조건이나 그룹 범위를 좁혀 주세요.")
    lines = []
    for key, items in groups.items():
        prefix = "; ".join(f"{_label(ref, sides)}={value[2]}" for ref, value in zip(plan.group_by, key))
        if plan.operation == "row_count":
            lines.append(f"{prefix}; 왼쪽 원본 행 기준 {len(items)}건")
            continue
        for reference in plan.column_ids:
            entries = [_value(item, reference) for item in items]
            if any(row is None or value in (None, "") for value, _, row in entries):
                raise RelationalError("집계 대상 값이 누락되어 전체 합계를 확정하지 않았습니다. 누락값은 0이 아닙니다.")
            result, _ = numeric_summary([value for value, _, _ in entries], [style for _, style, _ in entries], plan.statistic)
            if result is None:
                raise RelationalError("집계할 값의 숫자·통화·단위를 일관되게 확인하지 못했습니다.")
            lines.append((prefix + "; " if prefix else "") + f"{_label(reference, sides)}: {result}")
    return "\n".join(lines)


def relational_evidence(sides, needed, joined):
    evidence, seen = [], set()
    for side, table in sides.items():
        evidence.append(QuestionAnswerEvidence(kind=EvidenceKind.RANGE, sheet_name=table.sheet_name,
            reference=table.reference, label=f"{side} 연결 원본", description=f"연결 범위 전체 {len(table.rows)}개 행 대조"))
        columns = {column.id: column for column in table.columns}
        for item in joined:
            row = getattr(item, side)
            if row is None:
                continue
            for column in sorted(needed[side]):
                address = f"{column}{row.row_number}"
                identity = (table.sheet_name, address)
                if identity in seen or len(seen) >= 200:
                    continue
                seen.add(identity)
                evidence.append(QuestionAnswerEvidence(kind=EvidenceKind.CELL, sheet_name=table.sheet_name,
                    reference=address, label=columns[column].header, value=row.values[column],
                    formula=row.formulas.get(column), number_format=row.number_formats.get(column),
                    description="연결 키 또는 계산에 사용한 원본 셀"))
    return evidence


def _value(item, reference):
    side, column = reference.split(".")
    row = getattr(item, side)
    return (None, "General", None) if row is None else (row.values[column], row.number_formats.get(column, "General"), row)


def _label(reference, sides):
    side, column_id = reference.split(".")
    table = sides[side]
    column = next(column for column in table.columns if column.id == column_id)
    return f"{table.sheet_name}.{column.header}"


def _key_description(plan, sides):
    return ", ".join(f"{_label('left.' + key.left_column_id, sides)} = {_label('right.' + key.right_column_id, sides)}"
                     for key in plan.on)
