"""A ranking over groups mixed with their members ranks only the rows the question asks about."""
import asyncio
from types import SimpleNamespace

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_member_rows import member_ranking
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture

ROWS = [["Division and State", "Price"], ["New England", 28.3], ["Maine", 32.1], ["Vermont", 23.8],
        ["Pacific", 40.8], ["Hawaii", 47.2], ["Alaska", 29.4], ["U.S. Total", 18.2]]
GROUPS = {"New England", "Pacific", "U.S. Total"}


class Kinds:
    def __init__(self, status="selected"):
        self.status = status

    async def classify(self, question, header, labels):
        return SimpleNamespace(status=self.status, kind="주",
                               candidate_ids=[i for i, label in enumerate(labels) if label not in GROUPS])


def _rank(descending=True, limit=1, kinds=None):
    summary, index = table_fixture([(1, 1, ROWS)], sheet_name="Prices")
    table = build_query_tables(summary)[0]
    label, price = table.columns
    plan = TabularQueryPlan(operation="row_list", table_id=table.id, column_ids=[label.id, price.id],
                            order_by=price.id, descending=descending, limit=limit)
    return asyncio.run(member_ranking(plan, summary, index, "가격이 가장 높은 주는?", classifier=kinds or Kinds()))


def test_groups_and_totals_are_left_out_and_the_reading_is_stated():
    answer = _rank()
    assert answer.answer.splitlines()[-1] == "Price 기준 가장 높은 주: Hawaii 47.2"
    assert "제외: New England, Pacific, U.S. Total" in answer.answer
    assert answer.verification.level == "source_checked"
    assert {item.reference for item in answer.evidence} >= {"A6", "B6"}
    assert _rank(descending=False, limit=2).answer.splitlines()[-2:] == ["1. Vermont: 23.8", "2. Alaska: 29.4"]


def test_no_kind_read_leaves_the_refusal():
    assert _rank(kinds=Kinds("unnamed")) is None


def test_an_outline_group_is_ranked_by_its_total_row_not_its_first_member():
    outline = [["Sector", "2024"], ["Transport", 59.5], [None, 18.4], ["Transport total", 77.9],
               ["Waste", 5.1], [None, 2.0], ["Waste total", 7.1]]
    summary, index = table_fixture([(1, 1, outline)], sheet_name="Sectors")
    table = build_query_tables(summary)[0]
    label, value = table.columns
    plan = TabularQueryPlan(operation="row_list", table_id=table.id, column_ids=[label.id, value.id],
                            order_by=value.id, descending=True, limit=1)
    answer = asyncio.run(member_ranking(plan, summary, index, "가장 많은 부문은?", classifier=Kinds()))
    assert answer.answer.splitlines()[-1] == "2024 기준 가장 높은 그룹: Transport 77.9"  # its total row, not 59.5
