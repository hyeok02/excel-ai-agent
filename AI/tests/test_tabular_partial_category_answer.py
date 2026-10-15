"""A source category prefix may yield an explicit limited match, never green."""
import pytest

from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_partial_categories import partial_category_answer
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_routing import planned_tabular_answer
from tests.tabular_query_fixtures import table_fixture


def _fixture(question, values=None, filters=None, **updates):
    values = values or ["New (reviewed)", "New (scheduled)", "Existing", "New (reviewed)"]
    summary, index = table_fixture([(2, 1, [
        ["Asset", "State", "Change"],
        *[[name, state, value] for name, state, value in zip(
            ["First", "Second", "Third", "Fourth"], ["x", "x", "x", "o"], values)],
    ])])
    plan = TabularQueryPlan(operation="row_list", table_id=build_query_tables(summary)[0].id,
                            column_ids=["A", "B", "C"], filters=filters or [
                                TabularFilter(column_id="B", operator="equals", value="x"),
                                TabularFilter(column_id="C", operator="contains", value="New"),
                            ]).model_copy(update=updates)
    intent = QuestionIntent(False, "row_list", (), True, plan)
    return intent, summary, index, question


@pytest.mark.parametrize("phrase", ["New인", "'New'인", '“New”인'])
def test_annotated_categories_return_limited_literal_matches(phrase):
    args = _fixture(f"State가 x인 Asset 중 Change가 {phrase} Asset만 보여줘")
    answer = planned_tabular_answer(*args)
    assert answer.status == "limited" and answer.verification.level == "source_checked"
    assert "request_alignment" not in answer.verification.checks
    assert "category_match_interpreted" in answer.verification.checks
    assert "Asset: First" in answer.answer and "Asset: Second" in answer.answer
    assert "Asset: Third" not in answer.answer and "Asset: Fourth" not in answer.answer
    assert "같은 의미" in answer.answer and "contains 'New'" in answer.resolved_question


@pytest.mark.parametrize("bad_value", ["New", "Renew New", "Newer", "New category", "New ()"])
def test_partial_category_cannot_expand_to_unannotated_or_exact_values(bad_value):
    args = _fixture("State가 x인 Asset 중 Change가 New인 Asset", values=[bad_value, "Existing"])
    assert partial_category_answer(*args) is None


@pytest.mark.parametrize("question", [
    "State가 x인 Asset 중 Change가 정확히 New인 Asset",
    "State가 x인 Asset 중 Change가 New가 아닌 Asset",
    "State가 x인 Asset 중 Change가 Old인 Asset",
    "State가 x인 Asset 중 Change가 New 또는 Existing인 Asset",
    "State가 x인 Asset 중 New인 Asset",
])
def test_meaning_negation_or_ambiguous_subjects_are_not_reinterpreted(question):
    assert partial_category_answer(*_fixture(question)) is None


def test_partial_category_does_not_drop_another_explicit_filter():
    filters = [TabularFilter(column_id="C", operator="contains", value="New")]
    assert partial_category_answer(*_fixture("State가 x인 Asset 중 Change가 New인 Asset", filters=filters)) is None


def test_partial_category_does_not_ignore_other_numeric_conditions():
    args = _fixture("State가 x인 Asset 중 Change가 New인 Asset 중 Amount 100 초과인 것")
    assert partial_category_answer(*args) is None


@pytest.mark.parametrize("updates", [{"operation": "row_count"}, {"limit": 1}, {"order_by": "A"}])
def test_partial_category_is_not_an_aggregate_or_ranked_lookup(updates):
    assert partial_category_answer(*_fixture("State가 x인 Asset 중 Change가 New인 Asset", **updates)) is None
