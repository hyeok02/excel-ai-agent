"""Natural relative ranks preserve source scope without certifying semantic guesses."""
from dataclasses import replace

import pytest

from app.agent.query.intent_models import QuestionIntent
from app.agent.query.natural_relative_ranking import natural_relative_answer
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.support.large_workbook_fixtures import parsed, workbook, tiny_caps
from tests.support.replanning_adversarial import offline, Planner, run

QUESTION = "기준품 다음으로 가장 많이 팔린 품목이 뭐야?"
ROWS = [["Record", "Category", "Product", "Qty", "TotalPrice", "Region"],
        ["A", "Orchid", "One", 70, 70, "East"], ["B", "Fern", "Two", 50, 90, "West"],
        ["C", "Pine", "Three", 30, 80, "East"], ["D", "Orchid", "Four", 30, 30, "West"]]


def fixture(rows=None, *, hidden=None, extra=None):
    book = workbook({"Records": rows or ROWS, **(extra or {})})
    if hidden:
        book.active.column_dimensions[hidden].hidden = True
    summary, index, _ = parsed(book)
    table = next(table for table in build_query_tables(summary) if table.sheet_name == "Records")
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["D"],
        group_by=["B"], statistic="sum", order_by="D", limit=1,
        relative_rank={"column_id": "B", "value": "Orchid", "direction": "after"})
    return summary, index, plan


def intent(plan):
    return QuestionIntent(False, "aggregation", from_model=True, tabular_query=plan)


def answer(summary, index, plan, question=QUESTION):
    return natural_relative_answer(question, summary, index, intent(plan))


@pytest.mark.parametrize("streamed", [False, True])
@pytest.mark.parametrize("label,source_anchor", [("기준품", "Orchid"), ("Orchid", "Orchid"), ("만두", "Dumplings")])
def test_exact_or_translated_name_keeps_explicit_interpretation_not_request_badge(request, streamed, label, source_anchor):
    if streamed:
        request.getfixturevalue("tiny_caps")
    rows = [list(row) for row in ROWS]
    rows[1][1] = rows[4][1] = source_anchor
    summary, index, plan = fixture(rows)
    plan = plan.model_copy(update={"relative_rank": plan.relative_rank.model_copy(update={"value": source_anchor})})
    found = answer(summary, index, plan, QUESTION.replace("기준품", label))
    assert found is not None and found.status == "limited"
    assert found.verification.level == "source_checked" and "request_alignment" not in found.verification.checks
    assert "rank_interpretation" in found.verification.checks and found.evidence
    assert 'Category: "Fern"' in found.answer and "합계 50" in found.answer
    assert "해석했습니다" in found.answer and "Qty" in found.answer


@pytest.mark.parametrize("changes", [
    {"filters": [{"column_id": "F", "operator": "equals", "value": "East"}]},
    {"column_ids": ["E"], "order_by": "E"}, {"descending": False}, {"statistic": "average"},
    {"group_by": ["C"]}, {"relative_rank": {"column_id": "C", "value": "Orchid", "direction": "after"}, "group_by": ["C"]},
    {"relative_rank": {"column_id": "B", "value": "Orchid", "direction": "before"}},
    {"relative_rank": None}, {"limit": 2}, {"identity_column_ids": ["A"]},
])
def test_model_cannot_add_filters_change_measure_group_direction_or_operation(changes):
    summary, index, plan = fixture()
    altered = TabularQueryPlan.model_validate(plan.model_dump() | changes)
    assert answer(summary, index, altered) is None


@pytest.mark.parametrize("question", [
    "East에서 " + QUESTION, "2024년 " + QUESTION, "기준품만 다음으로 가장 많이 팔린 품목이 뭐야?",
    QUESTION.replace("기준품", "기준품 제외"), QUESTION + " East만", QUESTION + " 상위 2개",
    QUESTION.replace("다음", "이전"), QUESTION.replace("가장 많이 팔린", "판매금액이 가장 높은"),
])
def test_original_filter_period_direction_or_metric_cannot_disappear(question):
    summary, index, plan = fixture()
    assert answer(summary, index, plan, question) is None


@pytest.mark.parametrize("collision", ["quantity_header", "anchor_column", "source_spelling", "tail_source_spelling"])
def test_ambiguous_measure_anchor_or_existing_source_name_is_not_model_overridden(collision, request):
    rows = [list(row) for row in ROWS]
    if collision == "tail_source_spelling":
        request.getfixturevalue("tiny_caps")
        rows = [ROWS[0], ROWS[1], ROWS[2], *[[f"r{n}", "Birch", "Other", 1, 1, "East"] for n in range(10)],
                ["Last", "기준품", "Tail", 60, 60, "East"]]
    elif collision == "quantity_header":
        rows[0][4] = "Quantity"
    elif collision == "anchor_column":
        rows[1][2] = "Orchid"
    else:
        rows[2][1] = "기준품"
    summary, index, plan = fixture(rows)
    assert answer(summary, index, plan) is None


@pytest.mark.parametrize("hidden", ["B", "D"])
def test_natural_question_does_not_authorize_hidden_group_or_quantity_column(hidden):
    summary, index, plan = fixture(hidden=hidden)
    assert answer(summary, index, plan) is None


def test_revenue_question_and_metric_plan_must_agree():
    summary, index, plan = fixture()
    revenue = plan.model_copy(update={"column_ids": ["E"], "order_by": "E"})
    found = answer(summary, index, revenue, QUESTION.replace("가장 많이 팔린", "매출액이 가장 높은"))
    assert found is not None and found.verification.level == "source_checked"
    assert 'Category: "Fern"' in found.answer and "합계 90" in found.answer and "판매금액" in found.answer


@pytest.mark.parametrize("changes", [{"from_model": False}, {"whole_workbook": True}, {"kind": "row_count"}])
def test_non_aggregate_or_non_model_plan_cannot_activate_semantic_rewrite(changes):
    summary, index, plan = fixture()
    assert natural_relative_answer(QUESTION, summary, index, replace(intent(plan), **changes)) is None


def test_service_does_not_upgrade_natural_interpretation_or_call_generation():
    summary, index, plan = fixture()
    planner = Planner(intent(plan), None)
    found = run(QUESTION, summary, index, planner)
    assert found.status == "limited" and found.verification.level == "source_checked"
    assert "request_alignment" not in found.verification.checks and planner.repairs == []
    assert 'Category: "Fern"' in found.answer and len(planner.questions) == 1


@pytest.mark.parametrize("source_anchor", ["A-B", "A_B", "A B"])
def test_exact_original_identity_is_not_overridden_by_normalized_different_identity(source_anchor):
    rows = [list(row) for row in ROWS]
    rows[1][1] = rows[4][1] = source_anchor
    rows[2][1] = "AB"
    summary, index, plan = fixture(rows)
    plan = plan.model_copy(update={"relative_rank": plan.relative_rank.model_copy(update={"value": source_anchor})})
    assert answer(summary, index, plan, QUESTION.replace("기준품", "AB")) is None


def test_multiple_original_tables_cannot_be_arbitrarily_selected_by_model():
    other = [list(row) for row in ROWS]
    other[2][3], other[3][3] = 10, 80
    summary, index, plan = fixture(extra={"Other source": other})
    assert answer(summary, index, plan) is None


def test_incomplete_competing_source_cannot_be_ignored_because_anchor_is_not_sampled(tiny_caps):
    other = [ROWS[0], *[[f"Other{n}", "Birch", "Spare", n, n, "West"] for n in range(1, 10)]]
    other.append(["Late", "Orchid", "Tail", 100, 100, "East"])
    summary, index, plan = fixture(extra={"Other source": other})
    competing = next(table for table in build_query_tables(summary) if table.sheet_name == "Other source")
    assert not competing.complete
    assert not any("Orchid" in row.values.values() for row in competing.rows)
    assert answer(summary, index, plan) is None
