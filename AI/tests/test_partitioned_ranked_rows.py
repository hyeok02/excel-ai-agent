"""Bounded per-group row ranking and population-wide identity safety."""
import pytest

from app.agent.query.partitioned_ranked_rows import PartitionedRankedRows
from app.agent.query.tabular_catalog_models import QueryColumn, QueryRow, QueryTable
from app.agent.query.tabular_query_models import TabularQueryPlan


def accumulator(**changes):
    fields = dict(operation="row_list", table_id="t", column_ids=["A", "B"], group_by=["C"],
                  order_by="B", per_group_limit=2)
    fields.update(changes)
    table = QueryTable("t", "Rows", "A1:C20000", tuple(
        QueryColumn(key, name, f"Rows!{key}1", ())
        for key, name in [("A", "Record"), ("B", "Amount"), ("C", "Group")]), (), True)
    return PartitionedRankedRows(TabularQueryPlan(**fields), table)


def row(number, value, group="a", record=None, **changes):
    return QueryRow(number + 1, {"A": record or f"Record {number}", "B": value, "C": group}, **changes)


def test_every_group_retains_only_n_plus_one_boundary_rows():
    result = accumulator(identity_column_ids=["A"])
    for number in range(1, 20_001):
        assert result.add(row(number, number, str(number % 5)))
        assert result.retained_rows <= 15
    text, limitations = result.render()
    assert result.count == 20_000 and result.retained_rows == 15
    assert all(f"Record: Record {number};" in text for number in range(19_991, 20_001))
    assert "Record: Record 19990;" not in text and not limitations


def test_duplicate_entity_outside_selected_winners_invalidates_entire_answer():
    result = accumulator(identity_column_ids=["A"], per_group_limit=1)
    assert result.add(row(1, 1000, record="winner"))
    assert result.add(row(2, 5, record="duplicate"))
    assert not result.add(row(3, 1, record="duplicate"))
    assert result.render() == (None, [])
    assert not result.add(row(4, 2000))


def test_same_identity_in_distinct_groups_and_typed_ids_are_not_duplicates():
    result = accumulator(identity_column_ids=["A"])
    for number, value, group in [(1, 1, "a"), (2, "1", "a"), (3, 1, "b")]:
        assert result.add(QueryRow(number, {"A": value, "B": 10, "C": group}))
    assert result.render()[0] is not None


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_entity_identity_is_not_verified(value):
    result = accumulator(identity_column_ids=["A"])
    assert not result.add(QueryRow(2, {"A": value, "B": 10, "C": "a"}))
    assert result.render()[0] is None


def test_numeric_units_are_compared_within_each_group_not_between_groups():
    result = accumulator()
    assert result.add(row(1, 20, "a", number_formats={"B": "$0"}))
    assert result.add(row(2, 30, "b", number_formats={"B": "0%"}))
    assert result.render()[0] is not None
    assert not result.add(row(3, 1, "b", number_formats={"B": "$0"}))
    assert result.render()[0] is None


@pytest.mark.parametrize("setting,value", [("MAX_PARTITIONS", 1), ("MAX_RETAINED_ROWS", 1),
    ("MAX_RETAINED_CHARACTERS", 1), ("MAX_PARTITION_CHARACTERS", 1)])
def test_memory_limit_never_returns_partial_rank(monkeypatch, setting, value):
    monkeypatch.setattr(f"app.agent.query.partitioned_ranked_rows.{setting}", value)
    result = accumulator()
    success = result.add(row(1, 10, "a")) and result.add(row(2, 20, "b"))
    assert not success and result.render() == (None, [])


@pytest.mark.parametrize("setting", ["MAX_IDENTITIES", "MAX_IDENTITY_CHARACTERS"])
def test_identity_memory_limit_fails_closed(monkeypatch, setting):
    monkeypatch.setattr(f"app.agent.query.partition_rank_identity.{setting}", 1)
    result = accumulator(identity_column_ids=["A"])
    success = result.add(row(1, 10)) and result.add(row(2, 20))
    assert not success and result.render()[0] is None


def test_display_limit_is_explicit_and_never_cuts_a_group(monkeypatch):
    monkeypatch.setattr("app.agent.query.partitioned_ranked_rows.MAX_DISPLAY_ROWS", 3)
    result = accumulator()
    for number, group in enumerate(["a", "b", "a", "b"], 1):
        assert result.add(row(number, number, group))
    text, limitations = result.render()
    assert 'Group: "a"' in text and 'Group: "b"' not in text
    assert "4개 행 중 1개 그룹의 2개 행" in limitations[0]


def test_formula_without_cached_value_cannot_hide_outside_top_n():
    result = accumulator(per_group_limit=1)
    assert result.add(row(1, 100))
    assert not result.add(row(2, None, formulas={"B": "=EXTERNAL()"}))
    assert result.render()[0] is None
