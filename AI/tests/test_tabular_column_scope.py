import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("matrix,identity,hint,headers", [
    ([
        ["Reference", "Condition", "Release", "Operator remarks"],
        ["A1", "open", "ready", "Awaiting external response"],
        ["A2", "open", "ready", "Awaiting external response"],
        ["A3", "closed", "hold", None],
    ], "A", "B", ["Condition", "Release", "Operator remarks"]),
    ([
        ["검토 메모", "상태", "관리 코드", "확인 여부"],
        ["일정 변경 요청", "진행", "Q7", "완료"],
        ["일정 변경 요청", "진행", "Q8", "완료"],
        [None, "보류", "Q9", "미정"],
    ], "C", "B", ["검토 메모", "상태", "확인 여부"]),
])
def test_all_attributes_covers_source_columns_including_free_text(matrix, identity, hint, headers):
    summary, index = table_fixture([(1, 1, matrix)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(
        operation="frequencies", table_id=table.id, column_ids=[hint],
        column_scope="all_attributes", identity_column_ids=[identity],
    )
    answer = execute_tabular_query(plan, summary, index, "각 항목별로 요약해줘")
    assert answer is not None and answer.status == "answered"
    assert [line.split("’: ")[0] for line in answer.answer.splitlines()] == [f"‘{name}" for name in headers]
    assert "빈칸 1건" in answer.answer


@pytest.mark.parametrize("identities", [["B"], ["C"], ["Z"]])
def test_all_attributes_rejects_nonunique_blank_or_unknown_identity_columns(identities):
    summary, index = table_fixture([(1, 1, [
        ["Record", "Flag", "Comment"], ["A", "yes", "one"], ["B", "yes", None],
    ])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(
        operation="frequencies", table_id=table.id,
        column_scope="all_attributes", identity_column_ids=identities,
    )
    assert execute_tabular_query(plan, summary, index, "all fields") is None


def test_selected_column_scope_stays_narrow_and_empty_identity_includes_all():
    summary, index = table_fixture([(1, 1, [
        ["Record", "Flag", "Comment"], ["A", "yes", "note"], ["B", "no", "note"],
    ])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="frequencies", table_id=table.id, column_ids=["B"])
    answer = execute_tabular_query(plan, summary, index, "Flag only")
    assert "‘Flag’:" in answer.answer
    assert "‘Record’:" not in answer.answer and "‘Comment’:" not in answer.answer
    all_plan = plan.model_copy(update={"column_scope": "all_attributes", "column_ids": []})
    answer = execute_tabular_query(all_plan, summary, index, "all columns")
    assert all(f"‘{header}’:" in answer.answer for header in ["Record", "Flag", "Comment"])
