"""An all-row request must not gain a model-invented population restriction."""
import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.test_tabular_request_adversarial import _answer, _fixture
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("condition", [
    TabularFilter(column_id="D", operator="equals", value="Done"),
    TabularFilter(column_id="D", operator="not_equals", value="Pending"),
    TabularFilter(column_id="E", operator="equals", value=100),
    TabularFilter(column_id="E", operator="not_equals", value=100),
    TabularFilter(column_id="E", operator="is_blank"),
    TabularFilter(column_id="E", operator="not_blank"),
])
@pytest.mark.parametrize("question,operation,statistic", [
    ("전체 건수", "row_count", "all"),
    ("Amount 전체 합계", "numeric_summary", "sum"),
])
def test_unrequested_filters_cannot_narrow_the_whole_population(condition, question, operation, statistic):
    summary, index = _fixture()
    plan = TabularQueryPlan(operation=operation, table_id=build_query_tables(summary)[0].id,
                            column_ids=["E"], statistic=statistic, filters=[condition])
    kind = "row_count" if operation == "row_count" else "aggregation"

    assert _answer(question, plan, summary, index, kind) is None


def test_stated_category_does_not_authorize_a_second_numeric_filter():
    summary, index = _fixture()
    plan = TabularQueryPlan(operation="row_count", table_id=build_query_tables(summary)[0].id,
                            filters=[TabularFilter(column_id="D", operator="equals", value="Done"),
                                     TabularFilter(column_id="E", operator="equals", value=100)])

    assert _answer("Status가 Done인 전체 건수", plan, summary, index, "row_count") is None


def test_explicit_numeric_identity_remains_supported():
    from app.agent.query.tabular_request_extras import extra_filters_supported
    from app.agent.query.tabular_request_numeric import numeric_constraints_match

    summary, _ = _fixture()
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="row_count", table_id=table.id,
                            filters=[TabularFilter(column_id="E", operator="equals", value=100)])
    assert extra_filters_supported("Amount가 100인 건수", plan, table)
    assert numeric_constraints_match("Amount가 100인 건수", plan, table)


def test_unrequested_category_cannot_hide_inside_an_english_count_word():
    summary, index = _fixture()
    plan = TabularQueryPlan(operation="row_count", table_id=build_query_tables(summary)[0].id,
                            filters=[TabularFilter(column_id="D", operator="equals", value="Done")])
    assert _answer("count", plan, summary, index, "row_count") is None


@pytest.mark.parametrize("question", ["전체 건수 알려주세요", "전체 건수 상세히 설명해줘", "please report all rows"])
def test_unrecognized_polite_words_do_not_authorize_a_category_filter(question):
    summary, index = _fixture()
    plan = TabularQueryPlan(operation="row_count", table_id=build_query_tables(summary)[0].id,
                            filters=[TabularFilter(column_id="D", operator="equals", value="Done")])
    assert _answer(question, plan, summary, index, "row_count") is None


def test_source_company_name_without_legal_suffix_remains_answerable():
    summary, index = table_fixture([(6, 4, [
        ["Holder", "Quantity"], ["NORTH BRIDGE INC.", 42], ["Other Ltd.", 9],
    ])], sheet_name="Renamed register")
    plan = TabularQueryPlan(operation="lookup", table_id=build_query_tables(summary)[0].id,
                            column_ids=["E"], filters=[
                                TabularFilter(column_id="D", operator="equals", value="NORTH BRIDGE INC."),
                            ])
    answer = _answer("North Bridge의 Quantity", plan, summary, index, "cell_lookup")
    assert answer is not None and "42" in answer.answer
    assert answer.verification.level == "request_checked"
