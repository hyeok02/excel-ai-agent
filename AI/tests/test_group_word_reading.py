"""The column a "…별" word names is the grouping when the plan grouped by another."""
import asyncio
from datetime import datetime
from types import SimpleNamespace

from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_group_words import regrouped
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture

ROWS = [["Policy", "Expiry", "State"], ["P1", datetime(2025, 1, 2), "NY"], ["P2", datetime(2025, 1, 3), "NY"],
        ["P3", datetime(2025, 1, 3), "WI"]]


class Reads:
    def __init__(self, names):
        self.names, self.asked = names, []

    async def resolve(self, word, field, values):
        self.asked.append(word)
        if self.names.get(word) in values:
            return SimpleNamespace(status="resolved", candidate_id=values.index(self.names[word]))
        return SimpleNamespace(status="unmatched", candidate_id=None)


def _intent(summary, header):
    table = build_query_tables(summary)[0]
    group = next(column.id for column in table.columns if column.header == header)
    return QuestionIntent(False, "aggregation", (), True, TabularQueryPlan(
        operation="row_count", table_id=table.id, group_by=[group]))


def test_the_named_column_replaces_another_grouping_and_the_count_follows():
    summary, _ = table_fixture([(1, 1, ROWS)], sheet_name="PolicyData")
    intent = _intent(summary, "Expiry")
    moved = asyncio.run(regrouped(intent, summary, "주별 계약 건수 알려줘", Reads({"주별": "State"})))
    state = next(column.id for column in build_query_tables(summary)[0].columns if column.header == "State")
    assert moved.tabular_query.group_by == [state] and moved.tabular_query.operation == "row_count"


def test_nothing_changes_without_a_clear_reading_of_another_column():
    summary, _ = table_fixture([(1, 1, ROWS)], sheet_name="PolicyData")
    intent = _intent(summary, "Expiry")
    assert asyncio.run(regrouped(intent, summary, "주별 계약 건수 알려줘", Reads({}))) is intent
    assert asyncio.run(regrouped(intent, summary, "주별 계약 건수 알려줘", Reads({"주별": "Expiry"}))) is intent
    assert asyncio.run(regrouped(intent, summary, "계약 건수 알려줘", Reads({"주별": "State"}))) is intent
    stated, reads = _intent(summary, "State"), Reads({"주별": "Policy"})
    assert asyncio.run(regrouped(stated, summary, "State별 계약 건수 알려줘", reads)) is stated and reads.asked == []
