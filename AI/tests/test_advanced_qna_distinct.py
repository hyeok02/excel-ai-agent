"""Exact distinct populations retain source types and blank policies."""
from dataclasses import replace

import pytest

from tests.support.advanced_qna_fixtures import checked, distinct_plan, group_line, source
from tests.support.large_workbook_fixtures import ask, assert_not_certified, equal, offline, tiny_caps


@pytest.mark.parametrize("provider", [False, True])
def test_global_distinct_count_is_not_sum_of_group_distincts(provider):
    summary, index, _ = source()
    if not provider:
        index = replace(index, source_provider=None)
    answer = ask("Records 시트 Customer 중복 제외 개수 알려줘", summary, index, distinct_plan(summary))
    checked(answer, scan=False)
    assert "중복 제외 개수 5건" in answer.answer, answer.model_dump()


def test_grouped_distinct_counts_use_independent_sets(tiny_caps):
    summary, index, _ = source()
    answer = ask("Records 시트 Department별 Customer 중복 제외 개수 알려줘", summary, index,
                 distinct_plan(summary, group_by=["C"]))
    checked(answer, scan=True)
    for group, expected in [("Alpha", 3), ("Beta", 3), ("Gamma", 1)]:
        assert f"중복 제외 개수 {expected}건" in group_line(answer, group)


def test_distinct_count_does_not_merge_numeric_boolean_and_text_keys(tiny_caps):
    matrix = [["Record", "Amount", "Department", "Customer"], ["A", 1, "Only", True],
              ["B", 2, "Only", 1], ["C", 3, "Only", "1"], ["D", 4, "Only", 1],
              ["E", 5, "Only", None], ["F", 6, "Only", ""]]
    summary, index, _ = source(matrix)
    answer = ask("Records 시트 Customer 중복 제외 개수 알려줘", summary, index, distinct_plan(summary))
    checked(answer, scan=True)
    assert "중복 제외 개수 3건" in answer.answer, answer.model_dump()
    assert any("빈칸" in limitation for limitation in answer.limitations)


def test_multi_column_distinct_uses_tuples_not_summed_or_concatenated_keys(tiny_caps):
    matrix = [["Record", "Amount", "Department", "Customer"], ["A", 1, "ab", "c"],
              ["B", 2, "a", "bc"], ["C", 3, "ab", "c"], ["D", 4, "a", "c"]]
    summary, index, _ = source(matrix)
    answer = ask("Records 시트 Department와 Customer 조합의 중복 제외 개수 알려줘", summary, index,
                 distinct_plan(summary, columns=("C", "D")))
    checked(answer, scan=True)
    assert "중복 제외 개수 3건" in answer.answer, answer.model_dump()


def test_distinct_is_applied_after_row_filter(tiny_caps):
    summary, index, _ = source()
    answer = ask("Records 시트 State가 active인 Customer 중복 제외 개수 알려줘", summary, index,
                 distinct_plan(summary, filters=[equal("E", "active")]))
    checked(answer, scan=True)
    assert "중복 제외 개수 4건" in answer.answer, answer.model_dump()


def test_uncached_formula_distinct_key_cannot_be_treated_as_blank(tiny_caps):
    from tests.support.advanced_qna_fixtures import records
    matrix = records()
    matrix[-1][3] = "=MISSING_EXTERNAL_VALUE()"
    summary, index, _ = source(matrix)
    answer = ask("Records 시트 Customer 중복 제외 개수 알려줘", summary, index, distinct_plan(summary))
    assert_not_certified(answer)


def test_distinct_does_not_need_an_unselected_measure_formula(tiny_caps):
    from tests.support.advanced_qna_fixtures import records
    matrix = records()
    matrix[-1][1] = "=MISSING_EXTERNAL_VALUE()"
    summary, index, _ = source(matrix)
    answer = ask("Records 시트 Customer 중복 제외 개수 알려줘", summary, index, distinct_plan(summary))
    checked(answer, scan=True)


def test_distinct_capacity_failure_never_returns_a_partial_count(tiny_caps, monkeypatch):
    from app.agent.query import grouped_distinct_state
    monkeypatch.setattr(grouped_distinct_state, "MAX_DISTINCT_KEYS", 2)
    summary, index, _ = source()
    answer = ask("Records 시트 Customer 중복 제외 개수 알려줘", summary, index, distinct_plan(summary))
    assert_not_certified(answer)
    assert "full_source_scan" not in answer.verification.checks


def test_repeated_distinct_keys_do_not_exhaust_unique_key_capacity(tiny_caps, monkeypatch):
    from app.agent.query import grouped_distinct_state
    monkeypatch.setattr(grouped_distinct_state, "MAX_DISTINCT_KEYS", 2)
    matrix = [["Record", "Amount", "Department", "Customer"]]
    matrix.extend([f"Item{number}", number, "Only", f"Client{number % 2}"] for number in range(100))
    summary, index, _ = source(matrix)
    answer = ask("Records 시트 Customer 중복 제외 개수 알려줘", summary, index, distinct_plan(summary))
    checked(answer, scan=True)
    assert "중복 제외 개수 2건" in answer.answer


def test_overlapping_distinct_groups_cannot_use_summed_distincts_as_share_denominator(tiny_caps):
    summary, index, _ = source()
    answer = ask("Records 시트 Department별 Customer 중복 제외 개수의 전체 비중 알려줘", summary, index,
                 distinct_plan(summary, group_by=["C"], share_of_total=True))
    assert_not_certified(answer)
