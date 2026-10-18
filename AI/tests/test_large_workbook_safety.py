"""A source rescan must not turn an incomplete or contradictory query green."""
from dataclasses import replace

import pytest

from app.agent.query.tabular_query_models import TabularQueryPlan
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.workbook_source_models import SourceReadLimits
from tests.support.large_workbook_fixtures import (
    ask, assert_not_certified, equal, offline, parsed, plan_for, tiny_caps, workbook,
)


def matrix():
    return [["Record", "Amount", "Other"], *[[f"Item{n}", n, 100] for n in range(1, 9)]]


def test_late_duplicate_identity_prevents_certified_single_match(tiny_caps):
    rows = matrix()
    rows[1][0] = "Target"
    rows.append(["Target", 9000, 100])
    summary, index, _ = parsed(workbook({"Records": rows}))
    plan = plan_for(summary, operation="lookup", filters=[equal("A", "Target")])
    answer = ask("Records 시트 Record가 Target인 Amount 값은?", summary, index, plan)
    assert_not_certified(answer)


@pytest.mark.parametrize("limits", [
    SourceReadLimits(max_cells=10), SourceReadLimits(max_rows=3), SourceReadLimits(max_reads=0),
])
def test_scan_budget_failure_never_certifies_prefix_total(tiny_caps, limits):
    summary, index, _ = parsed(workbook({"Records": matrix()}), limits=limits)
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_not_certified(answer)
    assert "full_source_scan" not in answer.verification.checks


def test_cumulative_budget_exhausted_midscan_discards_the_partial_aggregate(tiny_caps):
    summary, index, _ = parsed(workbook({"Records": matrix()}), limits=SourceReadLimits(max_cells=30))
    with index.source_provider.scan_rows("Records", "A1:C3") as scan:
        assert len(list(scan)) == 3
    assert scan.complete
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_not_certified(answer)
    assert "full_source_scan" not in answer.verification.checks


@pytest.mark.parametrize("formula", ["=1+1", "=MISSING_EXTERNAL_VALUE()", "='[remote.xlsx]Sheet1'!A1"])
def test_uncached_tail_formula_is_not_treated_as_blank_or_zero(tiny_caps, formula):
    rows = matrix()
    rows.append(["Tail", formula, 100])
    summary, index, _ = parsed(workbook({"Records": rows}))
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_not_certified(answer)
    assert "합계 36" not in answer.answer


def test_uncached_tail_filter_cannot_be_assumed_to_exclude_a_record(tiny_caps):
    rows = matrix() + [["Tail", 9000, "=MISSING_EXTERNAL_VALUE()"]]
    summary, index, _ = parsed(workbook({"Records": rows}))
    plan = plan_for(summary, filters=[equal("C", 100)])
    answer = ask("Records 시트 Other가 100인 Amount 합계는?", summary, index, plan)
    assert_not_certified(answer)
    assert "합계 36" not in answer.answer


@pytest.mark.parametrize("last_format", ['"EUR" #,##0', "0.0%"])
def test_mixed_units_only_in_tail_do_not_pass_numeric_verification(tiny_caps, last_format):
    book = workbook({"Records": matrix()})
    for row in book.active.iter_rows(min_row=2, min_col=2, max_col=2):
        row[0].number_format = '"USD" #,##0'
    book.active["B9"].number_format = last_format
    summary, index, _ = parsed(book)
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_not_certified(answer)


@pytest.mark.parametrize("tail", ["12", True, "not recorded"])
def test_nonnumeric_tail_value_cannot_silently_disappear(tiny_caps, tail):
    rows = matrix()
    rows.append(["Tail", tail, 100])
    summary, index, _ = parsed(workbook({"Records": rows}))
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_not_certified(answer)


@pytest.mark.parametrize("mutation", ["column", "filter", "statistic", "digest"])
def test_full_rescan_does_not_authorize_wrong_plan_or_source(tiny_caps, mutation):
    summary, index, _ = parsed(workbook({"Records": matrix()}))
    plan = plan_for(summary)
    if mutation == "column":
        plan = plan.model_copy(update={"column_ids": ["C"]})
    elif mutation == "filter":
        plan = plan.model_copy(update={"filters": [equal("A", "Item1")]})
    elif mutation == "statistic":
        plan = plan.model_copy(update={"statistic": "average"})
    else:
        index = replace(index, source_digest="f" * 64)
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan)
    assert_not_certified(answer)


def test_excluded_sheet_cannot_be_added_back_by_a_model_plan(tiny_caps):
    book = workbook({"Records": matrix(), "Private": matrix()})
    book["Private"].sheet_state = "hidden"
    summary, index, _ = parsed(book)
    assert "Private" not in {sheet.name for sheet in summary.sheets}
    plan = TabularQueryPlan(operation="numeric_summary", table_id="Private!A1:C9", column_ids=["B"])
    answer = ask("Private 시트 Amount 합계는?", summary, index, plan)
    assert_not_certified(answer)


def test_filter_named_only_in_tail_cannot_be_dropped_from_the_plan(tiny_caps):
    rows = [["Record", "Amount", "Group"], *[[f"Item{n}", n, "ordinary"] for n in range(1, 9)]]
    rows.append(["Tail", 888, "special"])
    summary, index, _ = parsed(workbook({"Records": rows}))
    answer = ask("Records 시트 Group이 special인 Amount 합계는?", summary, index, plan_for(summary))
    assert_not_certified(answer)


def test_sample_header_cannot_override_the_actual_original_header(tiny_caps):
    summary, index, _ = parsed(workbook({"Records": matrix()}))
    header = next(cell for cell in summary.sheets[0].regions[0].analysis_rows[0] if cell["address"] == "B1")
    header["value"] = "Different"
    answer = ask("Records 시트 Different 합계는?", summary, index, plan_for(summary))
    assert_not_certified(answer)


def test_implicit_model_choice_cannot_expose_a_hidden_measure(tiny_caps):
    book = workbook({"Records": matrix()})
    book.active.column_dimensions["B"].hidden = True
    summary, index, _ = parsed(book)
    answer = execute_tabular_query(plan_for(summary), summary, index, "Records 시트 전체 숫자 합계는?")
    assert answer is None
