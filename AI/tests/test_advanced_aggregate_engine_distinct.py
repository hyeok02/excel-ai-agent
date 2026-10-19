"""Typed, bounded exact distinct counts and explicit incomplete tuple semantics."""
import pytest

from tests.test_advanced_aggregate_engine import accumulator, row


def distinct(**changes):
    return accumulator(operation="distinct_count", column_ids=["C"], **changes)


def test_global_distinct_preserves_type_case_and_complete_key_whitespace():
    result = distinct(group_by=[])
    for value in [True, 1, "1", "A", "a", " a ", "A", None, "", "  "]:
        assert result.add(row("unused", 0, value))
    text, limitations = result.render()
    assert "중복 제외 개수 6건" in text and "불완전한 값 제외 3개 행" in text
    assert limitations and "3개 행을 제외" in limitations[0]


def test_distinct_count_group_ranking_and_having_use_unique_not_row_counts():
    result = distinct(having=[dict(operator="greater_than", value=1)], limit=1)
    for group, value in [("repeats", "a"), ("repeats", "a"), ("repeats", "a"),
                         ("unique", "a"), ("unique", "b")]:
        assert result.add(row(group, 0, value))
    text, _ = result.render()
    assert '"unique"' in text and '"repeats"' not in text and "중복 제외 개수 2건" in text


def test_tuple_distinct_never_concatenates_values_or_counts_incomplete_tuple():
    result = accumulator(operation="distinct_count", column_ids=["B", "C"], group_by=[])
    for first, second in [("a-b", "c"), ("a", "b-c"), ("a", "b-c"), ("a", None)]:
        assert result.add(row("group", first, second))
    text, limitations = result.render()
    assert "중복 제외 개수 2건" in text and "불완전한 값 제외 1개 행" in text and limitations


def test_no_rows_global_distinct_is_zero_not_unknown():
    text, limitations = distinct(group_by=[]).render()
    assert "중복 제외 개수 0건" in text and not limitations


@pytest.mark.parametrize("setting,value", [("MAX_DISTINCT_KEYS", 1), ("MAX_DISTINCT_CHARACTERS", 25)])
def test_exact_distinct_memory_bound_discards_partial_result(monkeypatch, setting, value):
    monkeypatch.setattr(f"app.agent.query.grouped_distinct_state.{setting}", value)
    result = distinct(group_by=[])
    assert result.add(row("a", 0, "a"))
    assert not result.add(row("a", 0, "long-second-customer"))
    assert result.render()[0] is None


def test_distinct_budget_is_global_across_groups(monkeypatch):
    monkeypatch.setattr("app.agent.query.grouped_distinct_state.MAX_DISTINCT_KEYS", 1)
    result = distinct()
    assert result.add(row("first", 0, "same"))
    assert not result.add(row("other", 0, "same"))
    assert result.render()[0] is None


@pytest.mark.parametrize("value,kwargs", [
    (None, {"formulas": {"C": "=EXTERNAL()"}}), ("#N/A", {}),
    ("#REF!", {}), (float("nan"), {}), (float("inf"), {}),
    (5, {"number_formats": {"C": "yyyy-mm-dd"}}),
])
def test_unknown_or_error_identity_is_not_a_unique_customer(value, kwargs):
    result = distinct(group_by=[])
    assert not result.add(row("a", 0, value, **kwargs)) and result.render()[0] is None


def test_unit_conflict_in_an_unselected_group_invalidates_entire_distinct_ranking():
    result = distinct(limit=1)
    assert result.add(row("one", 0, 1, number_formats={"C": "$0"}))
    assert not result.add(row("two", 0, 2, number_formats={"C": "€0"}))
    assert result.render()[0] is None


def test_incomplete_tuple_still_cannot_hide_formula_error_in_other_component():
    result = accumulator(operation="distinct_count", column_ids=["B", "C"], group_by=[])
    assert not result.add(row("a", None, "#N/A")) and result.render()[0] is None


def test_overlapping_distinct_group_counts_cannot_become_additive_share():
    result = distinct(share_of_total=True)
    assert not result.add(row("a", 0, "customer")) and result.render()[0] is None
