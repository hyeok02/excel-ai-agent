"""Composite + Boolean plans run through the real service, not mocked answers."""
import pytest

from tests.support.replanning_adversarial import Planner, intent, offline, rejected, run
from tests.support.structured_adversarial import compound, plan, source
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("condition,total", [
    ("(Region = 'North' OR Region = 'South') AND NOT Status = 'Closed'", 50),
    ("Region = 'North' OR Region = 'South' AND Status = 'Closed'", 30),
    ("NOT (Region = 'West' OR Status = 'Closed')", 50),
])
def test_shared_boolean_scope_applies_to_every_independent_part(condition, total):
    summary, index, _ = source()
    texts = ["Amount 합계", "Amount 평균"]
    plans = [plan(summary, condition=condition), plan(summary, condition=condition, statistic="average")]
    planner = Planner(compound(texts, plans, prefix=condition), None)
    question = condition + ": " + "; ".join(texts)
    answer = run(question, summary, index, planner)
    assert answer.status == "answered", answer.model_dump()
    assert answer.verification.level == "request_checked", answer.model_dump()
    assert "compound_request_coverage" in answer.verification.checks
    assert f"합계 {total}" in answer.answer and f"평균 {total / 2:g}" in answer.answer
    assert {item.label.split(" · ")[0] for item in answer.evidence} == {"문항 1", "문항 2"}
    assert planner.questions == [question] and planner.repairs == []


@pytest.mark.parametrize("fault", ["wrong_metric", "wrong_statistic", "invalid_table"])
def test_one_bad_subplan_cannot_borrow_successful_part_badge_or_trigger_repairs(fault):
    summary, index, _ = source()
    second = plan(summary, statistic="average")
    second = second.model_copy(update={"wrong_metric": {"column_ids": ["E"]},
        "wrong_statistic": {"statistic": "sum"}, "invalid_table": {"table_id": "invalid"}}[fault])
    texts = ["Amount 합계", "Amount 평균"]
    planner = Planner(compound(texts, [plan(summary), second]), intent(plan(summary, statistic="average")))
    answer = run("; ".join(texts), summary, index, planner)
    assert answer.status == "limited" and answer.verification.level == "source_checked", answer.model_dump()
    assert "합계 100" in answer.answer and "확인 불가" in answer.answer
    assert "compound_request_coverage" not in answer.verification.checks
    assert all(item.label.startswith("문항 1 · ") for item in answer.evidence)
    assert planner.repairs == []


@pytest.mark.parametrize("mutation", ["drop", "reorder", "rewrite", "invent_prefix"])
def test_proposed_decomposition_cannot_edit_exact_source_question(mutation):
    summary, index, _ = source()
    texts = ["Amount 합계", "Amount 평균", "Costs 합계"]
    plans = [plan(summary), plan(summary, statistic="average"), plan(summary, column="E")]
    changed = {"drop": texts[:2], "reorder": list(reversed(texts)),
               "rewrite": [texts[0], "Amount 최댓값", texts[2]], "invent_prefix": texts}[mutation]
    prefix = "Region = 'North'" if mutation == "invent_prefix" else ""
    planner = Planner(compound(changed, plans, prefix=prefix), intent(plans[0]))
    answer = run("; ".join(texts), summary, index, planner)
    rejected(answer)
    assert answer.evidence == [] and planner.repairs == []


def test_boolean_parallel_table_ambiguity_cannot_be_resolved_by_model_choice():
    matrix = [["Record", "Region", "Status", "Amount", "Costs"],
              ["Alpha", "North", "Open", 10, 100], ["Beta", "South", "Open", 20, 200]]
    other = [matrix[0], ["Gamma", "North", "Open", 70, 700], ["Delta", "South", "Open", 80, 800]]
    summary, index = table_fixture([(1, 1, matrix), (7, 1, other)])
    condition = "Region = 'North' OR Region = 'South'"
    selected = plan(summary, condition=condition)
    planner = Planner(intent(selected), intent(selected))
    answer = run(condition + " Amount 합계", summary, index, planner)
    rejected(answer)
    assert planner.repairs == []


def test_explicit_table_range_can_resolve_boolean_ambiguity_without_model_guess():
    matrix = [["Record", "Region", "Status", "Amount", "Costs"],
              ["Alpha", "North", "Open", 10, 100], ["Beta", "South", "Open", 20, 200]]
    other = [matrix[0], ["Gamma", "North", "Open", 70, 700], ["Delta", "South", "Open", 80, 800]]
    summary, index = table_fixture([(1, 1, matrix), (7, 1, other)])
    condition = "Region = 'North' OR Region = 'South'"
    selected = plan(summary, condition=condition)
    planner = Planner(intent(selected), intent(selected))
    answer = run("'Arbitrary'!A1:E3 범위의 " + condition + " Amount 합계", summary, index, planner)
    assert answer.status == "answered" and answer.verification.level == "request_checked", answer.model_dump()
    assert "합계 30" in answer.answer


def test_boolean_part_local_filter_cannot_silently_be_dropped_from_following_part():
    summary, index, _ = source()
    condition = "Region = 'North' OR Region = 'South'"
    texts = [condition + " Amount 합계", "Amount 평균"]
    planner = Planner(compound(texts, [plan(summary, condition=condition),
                                     plan(summary, statistic="average")]), None)
    answer = run("; ".join(texts), summary, index, planner)
    assert answer.status == "limited" and answer.verification.level == "source_checked", answer.model_dump()
    assert "확인 불가" in answer.answer and planner.repairs == []
