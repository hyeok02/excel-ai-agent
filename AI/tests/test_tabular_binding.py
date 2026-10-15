from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


def test_exact_original_header_names_bind_to_catalog_ids():
    summary, index = table_fixture([(1, 1, [
        ["Reference", "Flag", "Comment"], ["A", "yes", "note"], ["B", "no", "note"],
    ])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(
        operation="frequencies", table_id=table.id, column_scope="all_attributes",
        identity_column_ids=["Reference"],
        filters=[TabularFilter(column_id="Flag", operator="equals", value="yes")],
    )
    bound = bind_tabular_plan(plan, table)
    assert bound.identity_column_ids == ["A"]
    assert bound.filters[0].column_id == "B"
    answer = execute_tabular_query(plan, summary, index, "all attributes for yes")
    assert answer is not None and "‘Flag’: ‘yes’ 1건" in answer.answer
    assert "‘Comment’: ‘note’ 1건" in answer.answer


def test_similar_or_ambiguous_column_names_are_not_guessed():
    summary, _ = table_fixture([(1, 1, [["B", "Flag"], ["record1", "yes"]])])
    table = build_query_tables(summary)[0]
    for selected in ("Fl", "B", "missing"):
        plan = TabularQueryPlan(operation="frequencies", table_id=table.id, column_ids=[selected])
        assert bind_tabular_plan(plan, table) is None
