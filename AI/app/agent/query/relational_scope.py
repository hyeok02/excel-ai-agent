"""Reject explicit scope contradictions; a model-selected join is not proof of intent."""
import re
from dataclasses import replace
from types import SimpleNamespace

from app.agent.query.relational_models import RelationalError
from app.agent.query.tabular_catalog_models import QueryRow, QueryTable
from app.agent.query.tabular_request_constraints import matches_constraints
from app.agent.query.tabular_request_scope import explicit_ranges

_MATCHED = re.compile(r"매칭된|일치하는|연결된\s*(?:행|항목|기록)|양쪽.*(?:있는|존재)|공통.*(?:행|항목)|matched|matching|inner\s+join", re.I)
_COUNT = re.compile(r"건수|몇\s*(?:건|개|행)|행\s*수|count|how many", re.I)
_STATS = {"sum": r"합계|총합|총액|합산|\bsum\b|\btotal\b", "average": r"평균|average|mean",
          "min": r"최소|최솟값|minimum|lowest", "max": r"최대|최댓값|maximum|highest"}


def validate_relational_scope(question, plan, sides, all_tables):
    text = _normal(question)
    selected = {table.id for table in sides.values()}
    names = {table.sheet_name for table in all_tables if _normal(table.sheet_name) in text}
    if names - {table.sheet_name for table in sides.values()}:
        raise RelationalError("질문에 지정한 시트와 연결 대상으로 선택한 시트가 다릅니다.")
    for sheet, reference in explicit_ranges(question):
        from app.agent.query.tabular_request_scope import _inside
        if not any(table.sheet_name == sheet and _inside(reference, table.reference) for table in sides.values()):
            raise RelationalError("질문에 지정한 셀 범위가 연결 대상 표에 포함되지 않습니다.")
        # Subranges require row-population planning; do not treat whole-table
        # totals as a correct answer about a smaller explicit range.
        if not any(table.sheet_name == sheet and reference == table.reference for table in sides.values()):
            raise RelationalError("부분 셀 범위를 지정한 표 연결은 전체 표 집계로 대신하지 않았습니다.")
    for table in all_tables:
        if table.id not in selected and any(_normal(value) in text for _, value in table.context if len(value) >= 4):
            raise RelationalError("질문에 지정한 다른 표의 제목이 선택된 연결 범위와 일치하지 않습니다.")
    if plan.population == "matched_only" and not _MATCHED.search(question):
        raise RelationalError("일치하지 않는 행을 제외할지 질문에서 확인되지 않아 임의로 제외하지 않았습니다.")
    if plan.population == "all_left" and any(item.side == "right" for item in plan.filters):
        raise RelationalError("오른쪽 표 조건으로 제외되는 왼쪽 행을 보존할지 확정해야 합니다. 일치하는 행만 요청해 주세요.")
    if plan.group_by and plan.operation in {"lookup", "row_list"}:
        raise RelationalError("그룹 집계를 일반 목록이나 단일 값으로 대신하지 않았습니다.")
    if plan.operation == "row_count" and not _COUNT.search(question):
        raise RelationalError("요청한 값을 행 건수로 대신하지 않았습니다.")
    requested = {kind for kind, pattern in _STATS.items() if re.search(pattern, question, re.I)}
    if requested and plan.operation != "numeric_summary":
        raise RelationalError("요청한 집계를 단일 값이나 목록으로 대신하지 않았습니다.")
    if plan.operation == "numeric_summary":
        if requested and requested != {plan.statistic}:
            raise RelationalError("질문의 집계 방식과 선택된 계산 방식이 다릅니다.")
    _check_keys(question, plan, sides)
    combined, check_plan = _constraint_view(plan, sides)
    _check_headers(text, check_plan, combined, sides)
    if not matches_constraints(question, check_plan, combined, [combined]):
        raise RelationalError("질문의 조건·값·집계 범위와 연결 계획을 일치시킬 수 없습니다.")
    # Source/calc verification alone cannot prove translated or implicit join
    # semantics. Relational answers deliberately remain SOURCE_CHECKED.


def _check_keys(question, plan, sides):
    for key in plan.on:
        labels = [next(column.header for column in sides[side].columns
                       if column.id == getattr(key, f"{side}_column_id")) for side in sides]
        if _normal(labels[0]) != _normal(labels[1]) and not all(_normal(label) in _normal(question) for label in labels):
            raise RelationalError("이름이 다른 연결 키의 대응 관계를 질문에서 확인하지 못했습니다. 두 키를 지정해 주세요.")


def _check_headers(text, plan, table, sides):
    mentioned = [column for column in table.columns if len(_normal(column.header)) >= 3 and _normal(column.header) in text]
    mentioned = [column for column in mentioned if not any(
        _normal(column.header) != _normal(other.header) and _normal(column.header) in _normal(other.header)
        for other in mentioned)]
    involved = set(plan.column_ids) | {item.column_id for item in plan.filters} | set(plan.key_ids)
    for column in mentioned:
        equivalent = {other.id for other in table.columns if _normal(other.header) == _normal(column.header)}
        if not involved & equivalent:
            raise RelationalError(f"질문한 ‘{column.header}’ 열이 연결 결과에 포함되지 않았습니다.")
    if re.search(r"별|by\s+", text, re.I) and plan.operation in {"numeric_summary", "row_count"} and not plan.group_ids:
        raise RelationalError("항목별 요청을 전체 합계 하나로 대신하지 않았습니다.")
    for reference in plan.group_ids:
        column = next(column for column in table.columns if column.id == reference)
        label = re.escape(_normal(column.header))
        if not re.search(rf"{label}\s*별|\bby\s+{label}(?![A-Za-z0-9])", text, re.I):
            raise RelationalError("질문에 지정하지 않은 그룹 기준을 임의로 추가하지 않았습니다.")


def _constraint_view(plan, sides):
    columns, rows = [], []
    for side, table in sides.items():
        columns.extend(replace(column, id=f"{side}.{column.id}") for column in table.columns)
    for side, table in sides.items():
        for row in table.rows:
            values = {column.id: None for column in columns}
            values.update({f"{side}.{column}": value for column, value in row.values.items()})
            styles = {f"{side}.{column}": style for column, style in row.number_formats.items()}
            rows.append(QueryRow(row.row_number, values, number_formats=styles))
    conditions = [item.model_copy(update={"column_id": f"{item.side}.{item.column_id}"}) for item in plan.filters]
    # Equality filters on joined keys constrain both equivalent columns. This
    # adds no execution predicate; it only exposes the equality to intent checks.
    for condition in list(conditions):
        for key in plan.on:
            pair = {f"left.{key.left_column_id}", f"right.{key.right_column_id}"}
            if condition.column_id in pair:
                conditions.append(condition.model_copy(update={"column_id": next(iter(pair - {condition.column_id}))}))
    contexts = tuple(context for table in sides.values() for context in table.context)
    view = QueryTable("join", "join", "A1:A1", tuple(columns), tuple(rows), True, context=contexts)
    adapted = SimpleNamespace(operation=plan.operation, statistic=plan.statistic, filters=conditions,
                              column_ids=plan.column_ids + plan.group_by, order_by=None, limit=None,
                              group_ids=plan.group_by, key_ids=[f"{side}.{getattr(key, f'{side}_column_id')}"
                                                             for key in plan.on for side in sides])
    return view, adapted


def _normal(value):
    return " ".join(str(value).casefold().split())
