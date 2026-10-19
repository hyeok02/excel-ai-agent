"""Reducer contracts independent of classification, samples, or file layout."""
from decimal import Decimal

import pytest

from app.agent.query.grouped_tabular_results import GroupedAccumulator
from app.agent.query.streaming_tabular_numeric import NumericAccumulator
from app.agent.query.tabular_catalog_models import QueryColumn, QueryRow, QueryTable
from app.agent.query.tabular_query_models import TabularQueryPlan


def accumulator(**changes):
    fields = dict(operation="numeric_summary", table_id="t", group_by=["A"],
                  column_ids=["B"], statistic="sum")
    fields.update(changes)
    table = QueryTable("t", "Sheet", "A1:C100", tuple(
        QueryColumn(key, name, f"Sheet!{key}1", ())
        for key, name in [("A", "Group"), ("B", "Amount"), ("C", "Region")]), (), True)
    return GroupedAccumulator(TabularQueryPlan(**fields), table)


def row(group, value, region="east", **kwargs):
    return QueryRow(2, {"A": group, "B": value, "C": region}, **kwargs)


def test_decimal_statistics_preserve_cancellation_and_exact_group_order():
    result = accumulator(order_by="B", limit=2)
    for value in [10 ** 35, 1, -(10 ** 35)]:
        assert result.add(row("tiny", value))
    assert result.add(row("zero", 0))
    text, _ = result.render()
    assert '"tiny"' in text and text.index('"tiny"') < text.index('"zero"')
    assert "Amount: 합계 1 " in text


def test_duplicate_bound_measure_ids_do_not_double_count():
    result = accumulator(column_ids=["B", "B"])
    assert result.add(row("group", 7))
    assert "Amount: 합계 7 " in result.render()[0]
    assert "합계 14 " not in result.render()[0]


def test_numeric_value_does_not_lose_average_precision():
    result = NumericAccumulator()
    for value in [1, 2, 3]:
        assert result.add(value, "General")
    assert result.value("sum") == Decimal(6)
    assert result.value("average") == Decimal(2)
    assert result.value("min") == Decimal(1) and result.value("max") == Decimal(3)
    assert result.value("all") is None


def test_keys_preserve_type_case_whitespace_and_missing_values():
    result = accumulator()
    for key in [True, 1, "1", "A", "a", " ", None, ""]:
        assert result.add(row(key, 1))
    assert len(result.state.groups) == 7
    text, _ = result.render()
    assert "논리값" in text and "숫자" in text and "문자" in text and "빈칸 (누락)" in text
    assert "행 개수 2건; Amount: 합계 2" in text


def test_no_numeric_cells_are_never_fabricated_as_zero_or_ranked():
    result = accumulator()
    assert result.add(row("missing", None)) and result.add(row("actual", 0))
    text, _ = result.render()
    assert "숫자 없음" in text and "0으로 간주하지 않음" in text
    ranked = accumulator(order_by="B", limit=1)
    assert ranked.add(row("missing", None)) and ranked.add(row("actual", 0))
    assert ranked.render()[0] is None


@pytest.mark.parametrize("setting,value", [("MAX_GROUPS", 1), ("MAX_AGGREGATES", 1),
                                          ("MAX_KEY_CHARACTERS", 15)])
def test_memory_bound_discards_previously_accumulated_answer(monkeypatch, setting, value):
    monkeypatch.setattr(f"app.agent.query.grouped_tabular_state.{setting}", value)
    result = accumulator()
    assert result.add(row("a", 1))
    assert not result.add(row("b", 1))
    assert result.render()[0] is None


def test_unit_conflict_in_losing_group_discards_answer():
    result = accumulator(order_by="B", limit=1)
    assert result.add(row("winner", 1000, number_formats={"B": "$0.00"}))
    assert not result.add(row("loser", 1, number_formats={"B": "€0.00"}))
    assert result.render()[0] is None


def test_multi_key_grouping_forms_tuple_not_concatenated_text():
    result = accumulator(group_by=["A", "C"])
    assert result.add(row("a-b", 3, "c"))
    assert result.add(row("a", 7, "b-c"))
    assert len(result.state.groups) == 2
    text, _ = result.render()
    assert "합계 3" in text and "합계 7" in text and "합계 10" not in text


def test_cutoff_tie_is_explicit_and_first_seen_wins():
    result = accumulator(order_by="B", limit=1)
    assert result.add(row("first", 1)) and result.add(row("later", 1))
    text, limitations = result.render()
    assert '"first"' in text and '"later"' not in text
    assert "동점" in text and limitations and "동점" in limitations[0]


def test_unbounded_group_output_discloses_display_cap_without_truncating_aggregation():
    result = accumulator()
    for number in range(51):
        assert result.add(row(f"group{number}", number))
    text, limitations = result.render()
    assert "51개 그룹" in text and '"group50"' not in text
    assert limitations and "50개 그룹만" in limitations[0]
