"""'The one after X', 'the N-th largest' and 'the largest except X' over source groups."""
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_routing import planned_tabular_answer
from tests.tabular_query_fixtures import table_fixture

ROWS = [["Category", "Product", "Amount"], ["Cookies", "Chip", 50], ["Bars", "Carrot", 30], ["Cookies", "Oat", 40],
        ["Crackers", "Wheat", 10], ["Bars", "Bran", 25], ["Snacks", "Pretzel", 5]]


def _answer(question, targets=(), rows=ROWS, **changes):
    summary, index = table_fixture([(1, 1, rows)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["C"], statistic="sum",
                            group_by=["A"], order_by="C", descending=True, limit=2).model_copy(update=changes)
    return planned_tabular_answer(QuestionIntent(False, "aggregation", tuple(targets), True, plan), summary, index, question)


def test_the_group_after_a_named_one_is_recomputed_from_every_row() -> None:
    answer = _answer("쿠키 다음으로 판매금액이 큰 품목은?", targets=["Cookies"])

    assert answer.answer.startswith("‘Cookies’ 다음은 ‘Bars’입니다 (‘Amount’ 합계 55)")
    assert "1. Cookies 90, 2. Bars 55, 3. Crackers 10, 4. Snacks 5" in answer.answer
    assert answer.verification.level == "source_checked" and answer.limitations


def test_an_exclusion_filter_or_an_ordinal_selects_the_position() -> None:
    excluded = [TabularFilter(column_id="A", operator="not_equals", value="Cookies")]
    assert "‘Bars’" in _answer("쿠키 빼고 가장 큰 품목은?", filters=excluded, limit=1).answer.split("(")[0]
    assert _answer("세 번째로 큰 품목은?").answer.startswith("3위는 ‘Crackers’입니다")


def test_an_unknown_anchor_or_a_missing_position_keeps_the_refusal() -> None:
    assert _answer("쿠키 다음으로 큰 품목은?").selected_tools == ["tabular_query"]
    assert _answer("열 번째로 큰 품목은?").selected_tools == ["tabular_query"]
    assert _answer("품목별 금액 비중은?", share_of_total=True).selected_tools == ["tabular_query"]


def test_a_plain_per_group_total_lists_every_group_with_its_conditions() -> None:
    plain = _answer("품목별 금액 합계는?")
    assert plain.answer == "‘Category’별 ‘Amount’ 합계 순위: 1. Cookies 90, 2. Bars 55, 3. Crackers 10, 4. Snacks 5."
    assert "조건 없이 전체 행" in plain.limitations[0]
    kept = [TabularFilter(column_id="B", operator="not_equals", value="Chip")]
    assert "‘Product’ not_equals Chip" in _answer("품목별 금액 합계는?", filters=kept).limitations[0]


def test_a_group_column_listed_as_a_measure_or_grouped_rows_still_rank() -> None:
    assert _answer("두 번째로 큰 품목은?", column_ids=["C", "A"]).answer.startswith("2위는 ‘Bars’입니다")
    rows = _answer("두 번째로 큰 품목은?", operation="row_list", column_ids=["A", "C"], statistic="all")
    assert rows.answer.startswith("2위는 ‘Bars’입니다")
    assert _answer("품목별 행", operation="row_list", statistic="all").selected_tools != ["ranked_group_query"]
    assert _answer("두 번째로 큰 품목은?", column_ids=["B", "C"]).selected_tools == ["tabular_query"]


def test_a_tied_position_names_every_group_with_that_total() -> None:
    tied = ROWS + [["Snacks", "Chips", 5]]
    assert "‘Snacks’도 같은 값이라 공동 순위입니다" in _answer("세 번째로 큰 품목은?", rows=tied).answer


def test_the_smallest_group_is_named_as_the_smallest() -> None:
    answer = _answer("금액이 가장 작은 품목은?").answer
    assert answer.startswith("가장 작은 값은 ‘Snacks’입니다 (‘Amount’ 합계 5).") and "순위(낮은 순): 1. Snacks 5" in answer
