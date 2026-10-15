from datetime import datetime

import pytest

from app.agent.query.comparison_scope import (
    question_date_bounds,
    requested_metric_group,
)
from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.tools.workbook_comparison_series import time_series_candidates


def test_period_end_uses_the_last_day_of_the_month() -> None:
    assert question_date_bounds("2024년 2월부터 2024년 2월까지") == (
        datetime(2024, 2, 1),
        datetime(2024, 2, 29),
    )
    assert question_date_bounds("2023년 2월까지") == (
        None,
        datetime(2023, 2, 28),
    )
    assert question_date_bounds("2025년 3월 재료비") == (
        datetime(2025, 3, 1),
        datetime(2025, 3, 31),
    )
    assert question_date_bounds("Output in March 2025") == (
        datetime(2025, 3, 1),
        datetime(2025, 3, 31),
    )
    assert question_date_bounds("2025/03 output") == (
        datetime(2025, 3, 1),
        datetime(2025, 3, 31),
    )


@pytest.mark.parametrize(
    "question",
    ("2024년 0월부터", "2024년 13월까지", "2025-13", "February 30, 2025"),
)
def test_invalid_date_cannot_fall_back_to_an_unbounded_range(question: str) -> None:
    start, end = question_date_bounds(question)

    assert start is not None and end is not None and start > end
    rows = [
        IndexedRow(
            "Data", number,
            (IndexedCell("Data", f"A{number}", value, None),),
        )
        for number, value in ((2, "2024-03-01"), (3, "2024-04-01"))
    ]
    assert time_series_candidates(
        rows,
        {("Data", number, "A"): "Date" for number in (2, 3)},
        (start, end),
    ) == []


@pytest.mark.parametrize(
    "question",
    (
        "March 15, 2025 sales",
        "15 March 2025 sales",
        "March 2025 15th sales",
        "2025-03-15 sales",
        "2025/03/15 sales",
        "2025.03.15 sales",
    ),
)
def test_common_exact_date_forms_are_supported(question: str) -> None:
    expected = datetime(2025, 3, 15)

    assert question_date_bounds(question) == (expected, expected)


@pytest.mark.parametrize(
    "question",
    ("2025년 3월부터 6월까지", "from March to June 2025"),
)
def test_abbreviated_same_year_ranges_are_supported(question: str) -> None:
    assert question_date_bounds(question) == (
        datetime(2025, 3, 1),
        datetime(2025, 6, 30),
    )


def test_english_group_alias_requires_a_complete_token() -> None:
    assert requested_metric_group("role 변화") == "role"
    assert requested_metric_group("roleplay score") is None


@pytest.mark.parametrize("years", ((2023, 2024), ("2023", "2024"), (2023.0, 2024.0)))
def test_year_columns_accept_numeric_and_text_years(years: tuple[object, object]) -> None:
    rows = [
        IndexedRow(
            "Data", number,
            (IndexedCell("Data", f"A{number}", value, None),),
        )
        for number, value in zip((2, 3), years)
    ]

    candidates = time_series_candidates(
        rows,
        {("Data", number, "A"): "Year" for number in (2, 3)},
        (None, None),
    )

    assert len(candidates) == 1
    assert [point[0] for point in candidates[0][1]] == [
        datetime(2023, 1, 1),
        datetime(2024, 1, 1),
    ]


def test_small_period_sequence_numbers_are_not_treated_as_calendar_years() -> None:
    rows = [
        IndexedRow(
            "Data", number,
            (IndexedCell("Data", f"A{number}", value, None),),
        )
        for number, value in ((2, 1), (3, 2))
    ]

    assert time_series_candidates(
        rows,
        {("Data", number, "A"): "Period" for number in (2, 3)},
        (None, None),
    ) == []
