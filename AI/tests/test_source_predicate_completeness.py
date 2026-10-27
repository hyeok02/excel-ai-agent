"""A local predicate must keep its full comparator, field and blank polarity."""
import pytest

from app.agent.query.source_aggregate_answers import source_aggregate_answer
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


def _fixture():
    summary, index = table_fixture([(1, 1, [
        ["Region", "Reading", "Class", "Temperature"],
        ["West", 10, "Active", 30], ["East", 20, None, 20],
        [None, 30, "Active", 10], ["West", 40, None, 40],
    ])], sheet_name="Observed Records")
    return summary, index, build_query_tables(summary)[0]


@pytest.mark.parametrize("phrase,expected", [
    ("20 이상인", 70), ("20 초과인", 50), ("20 이하인", 50),
    ("20 미만인", 30), ("20 보다 큰", 50), (">= 20인", 70),
])
def test_attached_numeric_comparator_is_not_mistaken_for_equality(phrase, expected):
    summary, index, _ = _fixture()
    question = f"Temperature가 {phrase} Reading 합계는 얼마야?"
    result = source_aggregate_answer(question, summary, index)
    assert result is not None and f"합계 {expected}" in result.answer, result
    assert result.verification.level == "request_checked"


@pytest.mark.parametrize("suffix", ["이 아닌", "이면서 35 이하인", "이거나 10 미만인", "이상한"])
def test_unparsed_comparison_remainder_is_not_silently_dropped(suffix):
    summary, index, _ = _fixture()
    assert source_aggregate_answer(f"Temperature가 20 이상{suffix} Reading 합계", summary, index) is None


@pytest.mark.parametrize("question", [
    "Region 값이 있는 행 중 Class가 빈칸인 Reading 합계",
    "Class가 빈칸인 행 중 Region 값이 있는 Reading 합계",
])
def test_blank_and_present_filters_keep_independent_polarities(question):
    summary, index, table = _fixture()
    filters = [TabularFilter(column_id="A", operator="not_blank"),
               TabularFilter(column_id="C", operator="is_blank")]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"],
                            statistic="sum", filters=filters)
    result = execute_tabular_query(plan, summary, index, question)
    assert result is not None and "합계 60" in result.answer, result
    assert result.verification.level == "request_checked"
    for wrong in [[], filters[:1], filters[1:],
                  [filters[0], TabularFilter(column_id="C", operator="not_blank")],
                  [*filters, TabularFilter(column_id="D", operator="not_blank")]]:
        assert execute_tabular_query(plan.model_copy(update={"filters": wrong}), summary, index, question) is None


@pytest.mark.parametrize("operator,expected", [(">=", 70), (">", 50), ("<=", 50), ("<", 30), ("≥", 70), ("≤", 50)])
def test_numeric_conditions_bind_quoted_source_headers(operator, expected):
    summary, index, _ = _fixture()
    result = source_aggregate_answer(f'"Temperature" {operator} 20 Reading 합계', summary, index)
    assert result is not None and f"합계 {expected}" in result.answer
    assert result.verification.level == "request_checked"


def test_quoted_value_named_like_a_header_is_not_a_numeric_field():
    summary, index, _ = _fixture()
    question = 'Region이 "Temperature" >= 20인 Reading 합계'
    assert source_aggregate_answer(question, summary, index) is None


@pytest.mark.parametrize("previous,expected", [
    ("Amount가 10 이상인 Score 합계", 6), ("Amount가 > 10인 Score 합계", 4),
])
def test_numeric_followup_keeps_the_independently_rechecked_threshold(previous, expected):
    from tests.test_conversation_aggregate_conditions import _run
    result = _run("그 조건에서 Score 합계는?", previous=previous)
    assert result.status == "limited" and f"합계 {expected}" in result.answer
    assert result.verification.level == "source_checked"
