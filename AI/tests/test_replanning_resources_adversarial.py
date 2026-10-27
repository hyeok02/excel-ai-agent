"""A retry shares original source safety limits; it cannot certify partial reads."""
import pytest

from app.agent.query.workbook_source_models import SourceReadLimits
from tests.support.large_workbook_fixtures import parsed, plan_for, tiny_caps, workbook
from tests.support.replanning_adversarial import Planner, intent, offline, rejected, run


def matrix():
    return [["Record", "Amount", "Currency"],
            *[[f"Item{number}", number, "USD"] for number in range(1, 10)]]


@pytest.mark.parametrize("invalid_first", [False, True])
@pytest.mark.parametrize("limits", [
    SourceReadLimits(max_cells=35), SourceReadLimits(max_rows=3), SourceReadLimits(max_reads=0),
])
def test_source_budget_is_not_reset_or_bypassed_by_replanning(tiny_caps, invalid_first, limits):
    summary, index, _ = parsed(workbook({"Records": matrix()}), limits=limits)
    if limits.max_cells == 35:
        with index.source_provider.scan_rows("Records", "A1:C3") as scan:
            assert len(list(scan)) == 3
        assert scan.complete
    plan = plan_for(summary)
    first = plan.model_copy(update={"table_id": "invalid"}) if invalid_first else plan
    planner = Planner(intent(first), intent(plan))
    answer = run("Records 시트 Amount 합계", summary, index, planner)
    rejected(answer)
    assert len(planner.repairs) == int(invalid_first)
    assert "full_source_scan" not in answer.verification.checks
    assert "합계 45" not in answer.answer


@pytest.mark.parametrize("invalid_first", [False, True])
@pytest.mark.parametrize("tail", ["formula", "currency", "nonnumeric"])
def test_unavailable_or_incompatible_tail_is_not_a_plan_error(tiny_caps, invalid_first, tail):
    rows = matrix()
    if tail == "formula":
        rows[-1][1] = "=UNAVAILABLE_EXTERNAL_VALUE()"
    elif tail == "currency":
        rows[-1][2] = "EUR"
    else:
        rows[-1][1] = "not recorded"
    summary, index, _ = parsed(workbook({"Records": rows}))
    plan = plan_for(summary)
    first = plan.model_copy(update={"table_id": "invalid"}) if invalid_first else plan
    planner = Planner(intent(first), intent(plan))
    answer = run("Records 시트 Amount 합계", summary, index, planner)
    rejected(answer)
    assert len(planner.repairs) == int(invalid_first)


def test_repair_cannot_add_filter_to_hide_conflicting_tail_currency(tiny_caps):
    from app.agent.query.tabular_query_models import TabularFilter

    rows = matrix()
    rows[-1][2] = "EUR"
    summary, index, _ = parsed(workbook({"Records": rows}))
    plan = plan_for(summary)
    revised = plan.model_copy(update={"filters": [
        TabularFilter(column_id="C", operator="equals", value="USD")]})
    planner = Planner(intent(plan.model_copy(update={"table_id": "invalid"})), intent(revised))
    rejected(run("Records 시트 Amount 합계", summary, index, planner))
    assert len(planner.repairs) == 1
