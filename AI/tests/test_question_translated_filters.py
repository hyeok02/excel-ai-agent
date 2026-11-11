"""A filter value the question names in other words is confirmed per word, then stated."""
import asyncio
from types import SimpleNamespace

from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_translated_filters import translated_filter_answer
from tests.tabular_query_fixtures import table_fixture

ROWS = [["Category", "Region", "Qty"], ["Cookies", "East", 10], ["Bars", "East", 20], ["Cookies", "West", 5]]
NAMES = {"쿠키": "Cookies", "동부": "East"}


class Resolver:
    def __init__(self, names=NAMES):
        self.names, self.calls = names, []

    async def resolve(self, word, field, values):
        self.calls.append(word)
        if word in self.names and self.names[word] in values:
            return SimpleNamespace(status="resolved", candidate_id=values.index(self.names[word]))
        return SimpleNamespace(status="unmatched", candidate_id=None)


def _ask(question, *filters, resolver=None):
    summary, index = table_fixture([(1, 1, ROWS)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["C"], statistic="sum",
                            filters=[TabularFilter(column_id=column, operator="equals", value=value)
                                     for column, value in filters])
    intent = QuestionIntent(False, "aggregation", (), True, plan)
    return asyncio.run(translated_filter_answer(question, summary, index, intent, resolver=resolver or Resolver()))


def test_a_word_confirmed_as_the_planned_value_answers_with_the_reading_shown():
    answer = _ask("쿠키 Qty 합계는?", ("A", "Cookies"))
    assert answer.status == "limited" and "합계 15" in answer.answer, answer.answer
    assert answer.answer.startswith("해석: ‘쿠키’ → Category = Cookies")
    assert answer.verification.level == "source_checked" and "semantic_alias_resolved" in answer.verification.checks
    both = _ask("동부 쿠키 Qty 합계는?", ("A", "Cookies"), ("B", "East"))
    assert "합계 10" in both.answer


def test_no_word_naming_the_value_or_a_value_the_source_lacks_answers_nothing():
    assert _ask("Qty 합계는?", ("A", "Cookies")) is None  # a filter no word asked for
    assert _ask("과자 Qty 합계는?", ("A", "Cookies")) is None  # the word names no source value
    assert _ask("쿠키 Qty 합계는?", ("A", "Crackers")) is None  # not a value of this column
    assert _ask("쿠키 Qty 합계는?", ("A", "Bars")) is None  # the word names a different value
    two = Resolver({"쿠키": "Cookies", "과자": "Cookies"})
    assert _ask("쿠키 과자 Qty 합계는?", ("A", "Cookies"), resolver=two) is None  # two words, one value
    assert _ask("Cookies Qty 합계는?", ("A", "Cookies")) is None  # stated already: the ordinary path answers


def test_a_phrase_and_its_own_word_are_one_mention():
    nested = Resolver({"쿠키": "Cookies", "쿠키 Qty": "Cookies"})
    assert _ask("쿠키 Qty 합계는?", ("A", "Cookies"), resolver=nested).answer.startswith("해석: ‘쿠키’ →")
