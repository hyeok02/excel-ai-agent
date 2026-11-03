"""A repaired plan answered by a recomputed group ranking is shown, limited, with its order."""
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import RelativeGroupRank, TabularQueryPlan
from tests.support.replanning_adversarial import Planner, intent, offline, run  # noqa: F401
from tests.tabular_query_fixtures import table_fixture

ROWS = [["Region", "Category", "Amount"], ["East", "Cookies", 50], ["West", "Bars", 30], ["East", "Bars", 40],
        ["North", "Crackers", 10], ["West", "Cookies", 25], ["North", "Bars", 5]]


def _repaired(question, first, **plan):
    summary, index = table_fixture([(1, 1, ROWS)])
    table = build_query_tables(summary)[0]
    revised = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["C"], statistic="sum",
                               **plan)
    first_plan = None if first is None else TabularQueryPlan(table_id=table.id, **first)
    planner = Planner(intent(first_plan), intent(revised))
    return run(question, summary, index, planner), planner


def test_a_grouped_replan_with_a_sort_alias_is_answered_from_every_row() -> None:
    answer, planner = _repaired("Amount가 가장 큰 Region은?", {"operation": "row_list", "column_ids": ["A", "C"]},
                                group_by=["A"], order_by="sum_Amount", limit=1)

    assert answer.answer.startswith("가장 큰 값은 ‘East’입니다 (‘Amount’ 합계 90)"), answer.model_dump()
    assert answer.status == "limited" and answer.selected_tools == ["ranked_group_query"]
    assert "plan_replanned" in answer.verification.checks and len(planner.repairs) == 1


def test_an_ordinal_replan_with_a_relative_rank_picks_that_position() -> None:
    answer, _ = _repaired("Amount가 두 번째로 큰 Category는?", None, group_by=["B"], order_by="C",
                          relative_rank=RelativeGroupRank(column_id="B", value="Cookies"))

    assert answer.answer.startswith("2위는 ‘Cookies’입니다"), answer.model_dump()
