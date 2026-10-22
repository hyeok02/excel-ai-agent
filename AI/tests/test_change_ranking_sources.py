"""Source populations must be complete and units proven, never guessed."""
from dataclasses import replace

import pytest
from openpyxl import Workbook

from app.agent.query.change_ranking_request import parse_change_ranking_request
from app.agent.query.change_ranking_sources import ranking_sources
from tests.support.large_workbook_fixtures import parsed

QUESTION = "전체 기간 중 인원이 제일 많이 감소한 부서는 어디야?"


def source(rows, *, formats=None):
    book = Workbook()
    book.active.title = "History"
    for row in rows:
        book.active.append(row)
    for coordinate, number_format in (formats or {}).items():
        book.active[coordinate].number_format = number_format
    summary, index, _ = parsed(book, filename="renamable.xlsx")
    return summary, index


def rank(summary, index, question=QUESTION):
    return ranking_sources(question, summary, index, parse_change_ranking_request(question))


def grouped(*, total=200):
    return source([["Date", "Total Employees", "Department", "Role", "Department"],
                   ["Date", "Total Employees", "Alpha", "Engineer", "Beta"],
                   ["2025-02-01", total, 80, 40, 120],
                   ["2025-01-01", 250, 100, 35, 150]])


def test_hierarchy_selects_only_requested_group_and_proves_parent_count_unit():
    result = rank(*grouped())
    assert not result.error
    assert [candidate.observations[0].label.value for candidate, _ in result.series] == ["Alpha", "Beta"]
    assert all(unit.known and unit.suffix == "명" for _, units in result.series for unit in units)
    assert {cell.address for _, units in result.series for unit in units for cell in unit.references} >= {
        "B2", "B3", "B4", "C3", "C4", "E3", "E4"}
    assert [point.period.month for point in result.series[0][0].observations] == [1, 2]


def test_a_nearby_count_field_does_not_prove_an_unreconciled_population_unit():
    result = rank(*grouped(total=999))
    assert not result.error
    assert all(not unit.known for _, units in result.series for unit in units)


def test_missing_selected_department_cannot_be_silently_dropped():
    summary, index = source([["Date", "Department", "Department"], ["Date", "Alpha", "Beta"],
                            ["2025-01-01", 100, 50], ["2025-02-01", None, 40]])
    assert rank(summary, index).error


def test_different_group_periods_are_not_intersected():
    summary, index = source([["Date", "Department", "Headcount"],
        ["2025-01-01", "Alpha", 100], ["2025-02-01", "Alpha", 90],
        ["2025-01-01", "Beta", 50], ["2025-03-01", "Beta", 40]])
    assert "날짜" in rank(summary, index).error


def test_source_hierarchy_must_exist_in_actual_cells():
    summary, index = grouped()
    rows = tuple(replace(row, cells=tuple(replace(cell, value="Role") if cell.address == "C1" else cell
                 for cell in row.cells)) for row in index.rows)
    assert rank(summary, replace(index, rows=rows, source_provider=None)).error


@pytest.mark.parametrize("question", [
    "서울 사업장만 전체 기간 중 인원이 제일 많이 감소한 부서는 어디야?",
    "인원 평균이 전체 기간 중 제일 많이 감소한 부서는 어디야?",
    "인원을 달러로 변환해서 전체 기간 중 제일 많이 감소한 부서는 어디야?",
])
def test_unbound_conditions_or_operations_are_not_certified(question):
    assert rank(*grouped(), question).error


def test_explicit_wrong_source_is_not_ignored():
    assert rank(*grouped(), "'Missing'!A1:E5 범위 " + QUESTION).error


def test_adjacent_quarter_does_not_use_monthly_intervals():
    assert rank(*grouped(), "인접 분기 인원이 가장 많이 감소한 부서는?").error


def test_unselected_entities_cannot_be_combined_in_a_long_source():
    summary, index = source([["Date", "Department", "Headcount", "Company"],
        ["2025-01-01", "Alpha", 100, "Company A"], ["2025-02-01", "Alpha", 90, "Company A"],
        ["2025-01-01", "Beta", 50, "Company B"], ["2025-02-01", "Beta", 40, "Company B"]])
    assert rank(summary, index).error


def test_named_group_restriction_is_not_consumed_as_an_unrestricted_population():
    assert rank(*grouped(), "Alpha 부서만 " + QUESTION).error


def test_a_currency_value_cannot_be_certified_as_headcount():
    summary, index = source([["Date", "Department", "Department"], ["Date", "Alpha", "Beta"],
        ["2025-01-01", 100, 50], ["2025-02-01", 90, 40]],
        formats={address: '$0' for address in ("B3", "B4", "C3", "C4")})
    assert rank(summary, index).error


@pytest.mark.parametrize("scenario", ["예상", "예산", "실적"])
def test_unqualified_source_cannot_certify_an_explicit_scenario(scenario):
    assert rank(*grouped(), scenario + " " + QUESTION).error
