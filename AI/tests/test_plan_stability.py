"""Plans that differ only in form, and readings a model may give either way, settle to one answer."""
import asyncio
from types import SimpleNamespace

from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_fixed_groups import without_fixed_groups
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_translated_filters import translated_filter_answer
from tests.tabular_query_fixtures import table_fixture

SALES = [["Region", "Category", "TotalPrice"], ["East", "Cookies", 10.5], ["West", "Bars", 3.0], ["East", "Bars", 2.0]]
GROUPS = [["Group", "England", "Wales"], ["All Persons", 100, 30], ["Males", 49, 14], ["Females", 51, 16]]


def _plan(rows, columns, filters, group_by=(), operation="numeric_summary"):
    summary, index = table_fixture([(1, 1, rows)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation=operation, table_id=table.id, column_ids=columns, group_by=list(group_by),
                            statistic="sum" if operation == "numeric_summary" else "all",
                            filters=[TabularFilter(column_id=column, operator="equals", value=value)
                                     for column, value in filters])
    return summary, index, QuestionIntent(False, "aggregation", (), True, plan)


def test_a_grouping_its_own_filter_fixes_to_one_value_is_dropped():
    summary, _, intent = _plan(SALES, ["C"], [("A", "East")], group_by=["A"])
    assert without_fixed_groups(intent, summary).tabular_query.group_by == []
    _, _, kept = _plan(SALES, ["C"], [("A", "East")], group_by=["B"])
    assert without_fixed_groups(kept, summary) is kept  # by Category within East is a real grouping


class Unread:
    def __init__(self, names=None):
        self.names = names or {}

    async def resolve(self, word, field, values):
        if self.names.get(word) in values:
            return SimpleNamespace(status="resolved", candidate_id=values.index(self.names[word]))
        return SimpleNamespace(status="unmatched", candidate_id=None)


def _ask(question, resolver, value="All Persons"):
    summary, index, intent = _plan(GROUPS, ["B"], [("A", value)], operation="lookup")
    intent = QuestionIntent(False, "cell_lookup", (), True, intent.tabular_query)
    return asyncio.run(translated_filter_answer(question, summary, index, intent, resolver=resolver))


def test_a_total_row_no_word_names_stands_for_the_column_and_is_stated():
    answer = _ask("England 인구 알려줘", Unread())
    assert answer is not None and "100" in answer.answer, answer
    assert answer.answer.startswith("해석: 전체 행 → Group = All Persons")


def _not_the_total_alone(answer):
    return answer is None or ("All Persons" in answer.answer and "Males" in answer.answer and "Females" in answer.answer)


def test_a_named_member_or_a_non_total_row_is_never_read_as_the_total():
    assert _not_the_total_alone(_ask("England 남성 인구 알려줘", Unread({"남성": "Males"})))
    assert _not_the_total_alone(_ask("England 인구 알려줘", Unread(), value="Females"))


def test_a_word_naming_a_column_the_plan_does_not_read_rejects_the_reading():
    assert _ask("영국 인구 알려줘", Unread({"영국": "Wales"})) is None  # the plan reads England
    answer = _ask("잉글랜드 인구 알려줘", Unread({"잉글랜드": "England"}))
    assert answer is not None and "‘잉글랜드’ → England" in answer.answer


def test_a_word_whose_pick_follows_the_listing_order_names_neither():
    class FirstFit(Unread):  # "성별" fits Males and Females alike: a model takes whichever is listed first
        async def resolve(self, word, field, values):
            fits = [value for value in values if value in ("Males", "Females")]
            if word == "성별" and fits:
                return SimpleNamespace(status="resolved", candidate_id=values.index(fits[0]))
            return await super().resolve(word, field, values)
    assert _not_the_total_alone(_ask("England 성별 인구", FirstFit(), value="Males"))
    assert "49" in _ask("England 남성 인구", Unread({"남성": "Males"}), value="Males").answer


def test_a_lookup_word_fitting_several_rows_shows_them_all_instead_of_one():
    rows = [["Measure", "2019"], ["Attack prevalence", 3.3], ["Current prevalence", 7.0]]
    summary, index, intent = _plan(rows, ["B"], [("A", "Attack prevalence")], operation="lookup")
    intent = QuestionIntent(False, "cell_lookup", (), True, intent.tabular_query)

    class FirstFit(Unread):
        async def resolve(self, word, field, values):
            fits = [value for value in values if "prevalence" in value]
            if word == "유병률" and fits:
                return SimpleNamespace(status="resolved", candidate_id=values.index(fits[0]))
            return await super().resolve(word, field, values)
    answer = asyncio.run(translated_filter_answer("2019 유병률은?", summary, index, intent, resolver=FirstFit()))
    assert answer is None or ("3.3" in answer.answer and "7" in answer.answer)


def test_an_unstated_contains_in_a_lookup_shows_every_row_and_never_widens_a_sum():
    rows = [["Measure", "2019"], ["Attack prevalence", 3.3], ["Current prevalence", 7.0]]
    summary, index, intent = _plan(rows, ["B"], [], operation="lookup")
    for operation, kind in (("lookup", "cell_lookup"), ("numeric_summary", "aggregation")):
        plan = intent.tabular_query.model_copy(update={"operation": operation, "statistic": "sum" if kind == "aggregation" else "all",
                                                       "filters": [TabularFilter(column_id="A", operator="contains", value="prevalence")]})
        answer = asyncio.run(translated_filter_answer("2019 유병률은?", summary, index,
                                                      QuestionIntent(False, kind, (), True, plan), resolver=Unread()))
        assert answer is None or (operation == "lookup" and "3.3" in answer.answer and "7" in answer.answer)
