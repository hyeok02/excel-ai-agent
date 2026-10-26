"""Unavailable historical samples must not compete with usable current values."""
from dataclasses import replace
import pytest

from app.agent.query.ambiguity_tables import candidates_for
from app.agent.query.tabular_catalog import build_query_tables
from tests.tabular_query_fixtures import table_fixture

QUESTION = "현재 직원 수 몇 명이야?"


def source(*, snapshot=False, available=True, partial=False):
    # Names and coordinates carry no role in selection.
    matrix = [["Company Name", "Headcount (Latest)"], ["#PEND", 120]] if snapshot else [
        ["Dates", "Company Name", "Headcount"], ["2025-12-31", "Alpha Co", 120]]
    left, a = table_fixture([(1, 1, matrix)], "Complete")
    right, b = table_fixture([(6, 3, [["Dates", "Company Name", "Headcount"],
        ["2024-12-31", "Alpha Co", 100], ["#PEND", "Alpha Co", "#PEND"]])], "Uncertain", complete=not partial)
    summary = replace(left, sheets=[*left.sheets, *right.sheets] if available else right.sheets,
                      sheet_count=2 if available else 1)
    index = replace(a, rows=(*a.rows, *b.rows) if available else b.rows)
    matches = [(table, column) for table in build_query_tables(summary) for column in table.columns
               if "Headcount" in column.header]
    return matches, index


@pytest.mark.parametrize("snapshot", [False, True])
@pytest.mark.parametrize("partial", [False, True])
def test_current_choices_exclude_uncertain_dated_samples_only_with_usable_alternative(snapshot, partial):
    matches, index = source(snapshot=snapshot, partial=partial)
    candidates = candidates_for(QUESTION, matches, index)
    assert len(candidates) == 1 and "Complete" in candidates[0].scope
    assert "120명" in candidates[0].details


def test_only_incomplete_source_remains_available_with_an_explicit_warning():
    matches, index = source(available=False)
    candidates = candidates_for(QUESTION, matches, index)
    assert len(candidates) == 1
    assert "최신 값 미확인" in candidates[0].details and "현재 값으로 확정하지 않았습니다" in candidates[0].details


@pytest.mark.parametrize("scope", ["Uncertain 시트", "'Uncertain'!C6:E8 범위"])
def test_explicit_scope_does_not_hide_the_requested_incomplete_source(scope):
    matches, index = source()
    candidates = candidates_for(scope + " " + QUESTION, matches, index)
    assert any("Uncertain" in candidate.scope for candidate in candidates)


def test_noncurrent_question_keeps_historical_source_examples():
    matches, index = source()
    assert len(candidates_for("직원 수 원본 항목을 보여줘", matches, index)) == 2


def test_missing_company_name_is_not_displayed_as_an_identifier():
    matches, index = source(snapshot=True)
    candidates = candidates_for(QUESTION, matches, index)
    assert "대상 미확인 (Company Name)" in candidates[0].details
    assert "Company Name: #PEND" not in candidates[0].details
    assert "120명" in candidates[0].details


def test_conflicting_current_values_remain_separate_choices_not_a_priority_winner():
    summary, index = table_fixture([
        (1, 1, [["Dates", "Company", "Headcount"], ["2025-12-31", "Alpha Co", 120]]),
        (6, 1, [["Company", "Headcount (Latest)"], ["Alpha Co", 130]]),
    ])
    matches = [(table, column) for table in build_query_tables(summary) for column in table.columns
               if "Headcount" in column.header]
    candidates = candidates_for(QUESTION, matches, index)
    assert len(candidates) == 2
    assert {value for value in ("120명", "130명") if any(value in candidate.details for candidate in candidates)} == {
        "120명", "130명"}
