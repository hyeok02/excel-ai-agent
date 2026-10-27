"""Plan repair must preserve the exact company, table and measure requested."""
import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.support.replanning_adversarial import Planner, intent, offline, rejected, repaired, run
from tests.tabular_query_fixtures import table_fixture


def source():
    summary, index = table_fixture([(5, 2, [
        ["Company", "Revenue", "Costs", "Currency"],
        ["Alpha Holdings", 10, 100, "USD"], ["Beta Holdings", 90, 900, "USD"],
        ["Alpha Holdings", 30, 300, "USD"],
    ])], sheet_name="Renamed source")
    [table] = build_query_tables(summary)
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
        column_ids=["C"], statistic="sum", filters=[
            TabularFilter(column_id="B", operator="equals", value="Alpha Holdings")])
    return summary, index, plan


@pytest.mark.parametrize("change", [
    {"column_ids": ["D"]}, {"statistic": "average"}, {"filters": []},
    {"filters": [TabularFilter(column_id="B", operator="equals", value="Beta Holdings")]},
])
def test_repair_cannot_change_company_or_same_unit_measure(change):
    summary, index, plan = source()
    question = "Company가 Alpha Holdings인 Revenue 합계"
    planner = Planner(intent(plan.model_copy(update={"table_id": "invalid"})),
                      intent(plan.model_copy(update=change)))
    answer = run(question, summary, index, planner)
    rejected(answer)
    assert len(planner.questions) == len(planner.repairs) == 1


def test_correct_company_repair_is_not_blanket_blocked():
    summary, index, plan = source()
    question = "Company가 Alpha Holdings인 Revenue 합계"
    planner = Planner(intent(plan.model_copy(update={"column_ids": ["ZZ"]})), intent(plan))
    answer = run(question, summary, index, planner)
    repaired(answer, planner, question)
    assert "합계 40" in answer.answer


@pytest.mark.parametrize("correct", [True, False])
def test_source_range_disambiguation_survives_invalid_initial_table(correct):
    summary, index = table_fixture([
        (4, 2, [["Company", "Revenue"], ["Alpha", 10], ["Beta", 20]]),
        (4, 7, [["Company", "Revenue"], ["Gamma", 70], ["Delta", 80]]),
    ], sheet_name="Moved source")
    left, right = sorted(build_query_tables(summary), key=lambda table: table.reference)
    selected, column = (left, "C") if correct else (right, "H")
    plan = TabularQueryPlan(operation="numeric_summary", table_id=selected.id,
                            column_ids=[column], statistic="sum")
    planner = Planner(intent(plan.model_copy(update={"table_id": "invalid"})), intent(plan))
    question = "'Moved source'!B4:C6 범위의 Revenue 합계"
    answer = run(question, summary, index, planner)
    if correct:
        repaired(answer, planner, question)
        assert "합계 30" in answer.answer
    else:
        rejected(answer)
        assert len(planner.repairs) <= 1


def test_actual_duplicate_table_ambiguity_cannot_trigger_model_selection():
    summary, index = table_fixture([
        (4, 2, [["Company", "Revenue"], ["Alpha", 10], ["Beta", 20]]),
        (4, 7, [["Company", "Revenue"], ["Gamma", 70], ["Delta", 80]]),
    ])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=["C"], statistic="sum")
    planner = Planner(intent(plan), intent(plan))
    answer = run("Revenue 합계", summary, index, planner)
    rejected(answer)
    assert answer.clarification_options and answer.evidence
    assert planner.repairs == []


@pytest.mark.parametrize("broken_first", [False, True])
def test_absent_company_is_not_repaired_into_an_existing_company(broken_first):
    summary, index, plan = source()
    missing = plan.model_copy(update={"statistic": "average", "filters": [
        TabularFilter(column_id="B", operator="equals", value="Missing Company")]})
    first = missing.model_copy(update={"table_id": "invalid"}) if broken_first else missing
    planner = Planner(intent(first), intent(plan))
    answer = run("Company가 Missing Company인 Revenue 평균", summary, index, planner)
    rejected(answer)
    assert len(planner.repairs) == int(broken_first)
