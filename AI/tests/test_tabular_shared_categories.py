"""Source-bound predicates work with compound IDs and repeated marker values."""
import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture
from tests.test_tabular_request_adversarial import _answer


def _fixture():
    return table_fixture([(5, 3, [
        ["Asset", "Connection", "Review", "Amount"],
        ["Unit #21", "x", "o", 10],
        ["Unit #22", "o", "x", 20],
        ["Unit #23", "x", "x", 30],
        ["Unit #24", None, None, 0],
    ])], sheet_name="Register")


def _plan(summary, operation="row_list", **updates):
    return TabularQueryPlan(operation=operation, table_id=build_query_tables(summary)[0].id,
                            column_ids=["C", "D"], **updates)


@pytest.mark.parametrize("question", [
    "Connection이 x인 Asset만 보여줘", "Connection 표시가 x인 Asset",
    "Connection is x, list Asset", "Connection = x rows",
])
def test_shared_category_is_bound_to_its_named_source_column(question):
    summary, index = _fixture()
    plan = _plan(summary, filters=[TabularFilter(column_id="D", operator="equals", value="x")])
    answer = _answer(question, plan, summary, index, "row_list")
    assert answer is not None
    assert "Unit #21" in answer.answer and "Unit #23" in answer.answer
    assert "Unit #22" not in answer.answer and "Unit #24" not in answer.answer
    assert answer.verification.level == "request_checked"


@pytest.mark.parametrize("filters", [
    [], [TabularFilter(column_id="E", operator="equals", value="x")],
    [TabularFilter(column_id="D", operator="equals", value="o")],
    [TabularFilter(column_id="D", operator="not_equals", value="x")],
    [TabularFilter(column_id="D", operator="equals", value="x"),
     TabularFilter(column_id="E", operator="equals", value="x")],
])
def test_repeated_marker_does_not_allow_omitted_swapped_or_extra_filters(filters):
    summary, index = _fixture()
    assert _answer("Connection이 x인 Asset만 보여줘", _plan(summary, filters=filters),
                   summary, index, "row_list") is None


def test_shared_marker_without_a_source_column_remains_ambiguous():
    summary, index = _fixture()
    plan = _plan(summary, filters=[TabularFilter(column_id="D", operator="equals", value="x")])
    assert _answer("x인 Asset만 보여줘", plan, summary, index, "row_list") is None


def test_multiple_mentions_of_the_same_marker_preserve_both_column_predicates():
    summary, index = _fixture()
    plan = _plan(summary, filters=[TabularFilter(column_id=column, operator="equals", value="x")
                                   for column in ("D", "E")])
    answer = _answer("Connection이 x이고 Review가 x인 Asset", plan, summary, index, "row_list")
    assert answer is not None and "Unit #23" in answer.answer and "Unit #21" not in answer.answer


@pytest.mark.parametrize("label", ["Unit #21", "Device AB-21", "Rack F21"])
def test_full_compound_source_key_satisfies_its_identifier_fragments(label):
    summary, index = table_fixture([(2, 2, [["Asset", "State"], [label, "x"], ["Other", "o"]])])
    plan = TabularQueryPlan(operation="lookup", table_id=build_query_tables(summary)[0].id,
                            column_ids=["C"], filters=[
                                TabularFilter(column_id="B", operator="equals", value=label)])
    answer = _answer(f"{label}의 State는 뭐야?", plan, summary, index, "cell_lookup")
    assert answer is not None and "State: x" in answer.answer


@pytest.mark.parametrize("selected", ["Unit #22", "#21", "Unit #210"])
def test_compound_id_support_does_not_accept_another_key_or_a_partial_key(selected):
    summary, index = _fixture()
    plan = _plan(summary, "lookup", filters=[
        TabularFilter(column_id="C", operator="equals", value=selected)])
    assert _answer("Unit #21의 Connection은 뭐야?", plan, summary, index, "cell_lookup") is None


def test_new_numeric_filter_keeps_existing_marker_and_its_boundary():
    summary, index = _fixture()
    plan = _plan(summary, filters=[TabularFilter(column_id="D", operator="equals", value="x"),
                                   TabularFilter(column_id="F", operator="less_than", value=30)])
    answer = _answer("Connection이 x이고 Amount가 30 미만인 Asset", plan, summary, index, "row_list")
    assert answer is not None and "Unit #21" in answer.answer and "Unit #23" not in answer.answer
    plan.filters[1].operator = "less_than_or_equal"
    assert _answer("Connection이 x이고 Amount가 30 미만인 Asset", plan, summary, index, "row_list") is None


def test_missing_marker_and_zero_amount_are_not_substituted_for_each_other():
    summary, index = _fixture()
    plan = _plan(summary, filters=[TabularFilter(column_id="D", operator="equals", value="x"),
                                   TabularFilter(column_id="F", operator="equals", value=0)])
    answer = _answer("Connection이 x이고 Amount가 0인 Asset", plan, summary, index, "row_list")
    assert answer is not None and "맞는 행이 없습니다" in answer.answer


@pytest.mark.parametrize("extra", [False, True])
def test_question_mark_in_source_is_not_an_implicit_predicate(extra):
    summary, index = table_fixture([(2, 2, [
        ["Asset", "Connection"], ["Unit #21", "x"], ["Unit #22", "?"],
    ])])
    filters = [TabularFilter(column_id="B", operator="equals", value="Unit #21")]
    if extra:
        filters.append(TabularFilter(column_id="C", operator="equals", value="?"))
    plan = TabularQueryPlan(operation="lookup", table_id=build_query_tables(summary)[0].id,
                            column_ids=["C"], filters=filters)
    answer = _answer("Unit #21의 Connection 표시는 뭐야?", plan, summary, index, "cell_lookup")
    assert (answer is None) == extra


def test_explicit_question_mark_marker_can_still_be_filtered():
    summary, index = table_fixture([(2, 2, [["Asset", "Connection"], ["One", "?"], ["Two", "x"]])])
    plan = TabularQueryPlan(operation="row_list", table_id=build_query_tables(summary)[0].id,
                            column_ids=["B"], filters=[
                                TabularFilter(column_id="C", operator="equals", value="?")])
    answer = _answer("Connection이 ?인 Asset", plan, summary, index, "row_list")
    assert answer is not None and "Asset: One" in answer.answer and "Asset: Two" not in answer.answer


def test_longest_named_header_binds_shared_values_without_matching_its_suffix():
    summary, index = table_fixture([(2, 2, [
        ["Asset", "Review Status", "Status"], ["One", "x", "o"], ["Two", "o", "x"],
    ])])
    plan = TabularQueryPlan(operation="row_list", table_id=build_query_tables(summary)[0].id,
                            column_ids=["B"], filters=[
                                TabularFilter(column_id="C", operator="equals", value="x")])
    answer = _answer("Review Status가 x인 Asset", plan, summary, index, "row_list")
    assert answer is not None and "Asset: One" in answer.answer and "Asset: Two" not in answer.answer


def test_repeated_markers_preserve_explicit_negation():
    summary, index = _fixture()
    plan = _plan(summary, filters=[TabularFilter(column_id="D", operator="not_equals", value="x")])
    answer = _answer("Connection이 x가 아닌 Asset", plan, summary, index, "row_list")
    assert answer is not None and "Unit #22" in answer.answer and "Unit #21" not in answer.answer
