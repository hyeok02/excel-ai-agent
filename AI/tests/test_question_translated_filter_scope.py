"""Translated filters cover OR'ed values, up to four conditions and columns longer than one request."""
import asyncio
from types import SimpleNamespace

from app.agent.query.boolean_filter_models import BooleanFilterExpression
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_translated_filters import translated_filter_answer
from tests.tabular_query_fixtures import table_fixture


class Resolver:
    def __init__(self, names, elsewhere=None):
        self.names, self.elsewhere, self.calls = names, elsewhere or {}, 0

    async def resolve(self, word, field, values):
        self.calls += 1
        if self.names.get(word) in values:
            return SimpleNamespace(status="resolved", candidate_id=values.index(self.names[word]))
        if self.elsewhere.get(word) in values:
            return SimpleNamespace(status="ambiguous", candidate_id=None)
        return SimpleNamespace(status="unmatched", candidate_id=None)


def _ask(rows, question, values, resolver, expression=None):
    summary, index = table_fixture([(1, 1, rows)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"], statistic="sum",
                            filters=[TabularFilter(column_id="A", operator="equals", value=value) for value in values],
                            filter_expression=expression)
    intent = QuestionIntent(False, "aggregation", (), True, plan)
    return asyncio.run(translated_filter_answer(question, summary, index, intent, resolver=resolver))


ROWS = [["Category", "Qty"], ["Cookies", 10], ["Bars", 20], ["Crackers", 5]]
EITHER = BooleanFilterExpression(operator="or", children=[
    BooleanFilterExpression(operator="predicate", filter_index=0),
    BooleanFilterExpression(operator="predicate", filter_index=1)])


def test_two_values_joined_by_or_are_each_named_by_their_own_word():
    resolver = Resolver({"쿠키": "Cookies", "크래커": "Crackers"})
    answer = _ask(ROWS, "쿠키랑 크래커 Qty 합계는?", ["Cookies", "Crackers"], resolver, EITHER)
    assert answer is not None and "합계 15" in answer.answer, answer
    assert "‘쿠키’ → Category = Cookies" in answer.answer and "‘크래커’ → Category = Crackers" in answer.answer


LONG = [["Category", "Qty"], *([f"Item {number:03d}", 1] for number in range(600)), ["Cookies", 7]]


def test_a_long_column_is_asked_in_parts_and_the_word_must_match_nothing_elsewhere():
    resolver = Resolver({"쿠키": "Cookies"})
    answer = _ask(LONG, "쿠키 Qty 합계는?", ["Cookies"], resolver)
    assert answer is not None and "합계 7" in answer.answer
    assert resolver.calls == 3  # one call per part of 601 values
    unsure = Resolver({"쿠키": "Cookies"}, elsewhere={"쿠키": "Item 599"})
    assert _ask(LONG, "쿠키 Qty 합계는?", ["Cookies"], unsure) is None


def test_a_column_beyond_the_request_budget_is_not_translated():
    huge = [["Category", "Qty"], *([f"Item {number:04d}", 1] for number in range(1_100)), ["Cookies", 7]]
    assert _ask(huge, "쿠키 Qty 합계는?", ["Cookies"], Resolver({"쿠키": "Cookies"})) is None


def test_values_listed_in_the_question_must_be_exactly_the_or_planned():
    from app.agent.query.tabular_execution import execute_tabular_query
    summary, index = table_fixture([(1, 1, ROWS)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"], statistic="sum",
                            filters=[TabularFilter(column_id="A", operator="equals", value=value)
                                     for value in ("Cookies", "Crackers")], filter_expression=EITHER)
    intent = QuestionIntent(False, "aggregation", (), True, plan)
    ask = lambda question: execute_tabular_query(plan, summary, index, question, intent)
    assert "합계 15" in ask("Cookies랑 Crackers Qty 합계는?").answer
    assert "합계 15" in ask("Cookies, Crackers의 Qty 합계는?").answer
    assert ask("Cookies와 Bars Qty 합계는?") is None
    assert ask("Cookies랑 Crackers 그리고 Bars Qty 합계는?") is None


def test_contains_is_read_as_equals_only_when_the_source_makes_them_the_same_rows():
    contains = lambda value: TabularFilter(column_id="A", operator="contains", value=value)
    summary, index = table_fixture([(1, 1, ROWS + [["Cookies & Cream", 100]])])
    table = build_query_tables(summary)[0]
    def ask(question, value):
        plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"], statistic="sum",
                                filters=[contains(value)])
        intent = QuestionIntent(False, "aggregation", (), True, plan)
        return asyncio.run(translated_filter_answer(question, summary, index, intent,
                                                    resolver=Resolver({"크래커": "Crackers", "쿠키": "Cookies"})))
    assert "합계 5" in ask("크래커 Qty 합계는?", "Crackers").answer
    assert ask("쿠키 Qty 합계는?", "Cookies") is None  # "Cookies & Cream" also contains it


def test_an_or_question_reads_its_metric_word_among_the_headers_before_answering():
    resolver = Resolver({"쿠키": "Cookies", "크래커": "Crackers", "판매수량": "Qty"})
    answer = _ask(ROWS, "쿠키랑 크래커 판매수량 합계는?", ["Cookies", "Crackers"], resolver, EITHER)
    assert answer is not None and "합계 15" in answer.answer, answer
    assert "‘판매수량’ → Qty" in answer.answer
    unknown = Resolver({"쿠키": "Cookies", "크래커": "Crackers"})  # 판매수량 names no header: nothing is read
    assert _ask(ROWS, "쿠키랑 크래커 판매수량 합계는?", ["Cookies", "Crackers"], unknown, EITHER) is None


def test_a_word_only_one_condition_can_take_is_not_counted_for_another():
    rows = [["Category", "Product", "Qty"], ["Cookies", "Chocolate Chip", 3], ["Cookies", "Oatmeal", 4],
            ["Bars", "Carrot", 9]]
    summary, index = table_fixture([(1, 1, rows)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["C"], statistic="sum",
                            filters=[TabularFilter(column_id="A", operator="equals", value="Cookies"),
                                     TabularFilter(column_id="B", operator="equals", value="Chocolate Chip")])
    intent = QuestionIntent(False, "aggregation", (), True, plan)

    class ParentToo(Resolver):  # "초코칩" also names its category, as a model may answer
        async def resolve(self, word, field, values):
            if word == "초코칩" and "Cookies" in values:
                return SimpleNamespace(status="resolved", candidate_id=values.index("Cookies"))
            return await super().resolve(word, field, values)
    resolver = ParentToo({"쿠키": "Cookies", "초코칩": "Chocolate Chip"})
    answer = asyncio.run(translated_filter_answer("쿠키 초코칩 Qty 합계는?", summary, index, intent, resolver=resolver))
    assert answer is not None and "합계 3" in answer.answer, answer
    assert "‘쿠키’ → Category = Cookies" in answer.answer and "‘초코칩’ → Product = Chocolate Chip" in answer.answer
