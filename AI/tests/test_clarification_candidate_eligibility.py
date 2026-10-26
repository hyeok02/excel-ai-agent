"""Only complete source proof may eliminate unavailable or mismatched choices."""
import pytest

from tests.test_clarification_source_previews import choices


@pytest.mark.parametrize("missing", [None, "", "#PEND", "#N/A", "#REF!"])
def test_complete_candidates_with_no_stored_values_are_not_offered(missing):
    result, *_ = choices([["Company", "Headcount"], ["Alpha Co", missing]])
    assert result == []


def test_latest_missing_value_never_offers_the_older_value_as_current():
    result, *_ = choices([
        ["Date", "Company", "Headcount"],
        ["2024-12-31", "Alpha Co", 100], ["2025-12-31", "Alpha Co", "#PEND"],
    ])
    assert result == []


def test_incomplete_source_is_not_discarded_because_its_sample_is_empty():
    result, *_ = choices([["Company", "Headcount"], ["Alpha Co", "#PEND"]], complete=False)
    assert len(result) == 1 and "원본 값 미확인" in result[0].details


@pytest.mark.parametrize("dimension,values", [("Country", ["South Korea", "Japan"]),
    ("Country / Region Name", ["South Korea", "Japan"]), ("CountryName", ["South Korea", "Japan"]),
    ("Department", ["Engineering", "Support"]), ("Department Name", ["Engineering", "Support"]),
    ("부서명", ["Engineering", "Support"])])
def test_detail_breakdown_cannot_be_offered_as_current_whole_headcount(dimension, values):
    matrix = [[dimension, "Headcount"], *[[value, count] for value, count in zip(values, [10, 20])]]
    assert choices(matrix)[0] == []
    assert len(choices(matrix, question=f"현재 {dimension}별 직원 수 몇 명이야?")[0]) == 1
    assert len(choices(matrix, question=f"현재 {values[0]} 직원 수 몇 명이야?")[0]) == 1


def test_total_row_or_explicit_scope_keeps_a_breakdown_candidate_available():
    matrix = [["Country", "Headcount"], ["South Korea", 10], ["Japan", 20], ["Total", 30]]
    assert len(choices(matrix)[0]) == 1
    matrix = matrix[:-1]
    assert len(choices(matrix, question="'Arbitrary'!A1:B3 현재 직원 수 몇 명이야?")[0]) == 1


def test_country_metadata_of_separate_companies_is_not_a_country_breakdown():
    matrix = [["Company", "Country", "Headcount"], ["Alpha Co", "South Korea", 10], ["Beta Co", "Japan", 20]]
    result, *_ = choices(matrix)
    assert len(result) == 1 and "Alpha Co" in result[0].details and "Beta Co" in result[0].details


def test_metric_candidate_never_uses_old_value_when_newest_formula_cache_is_missing():
    from dataclasses import replace
    from app.agent.query.ambiguity_metrics import metric_candidates
    from tests.test_metric_observation_answers import _index
    index = _index({"Report": {"A1": "Amounts in USD millions", "A2": "Period",
                               "B2": "2024-01-01", "C2": "2025-01-01",
                               "A3": "Revenue", "B3": 100, "C3": None}})
    index = replace(index, rows=tuple(replace(row, cells=tuple(
        replace(cell, formula="=REMOTE()") if cell.address == "C3" else cell for cell in row.cells))
        for row in index.rows))
    assert metric_candidates("최신 Revenue는?", index) == []
