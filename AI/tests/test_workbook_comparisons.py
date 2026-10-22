import pytest

from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.tools.workbook_comparisons import build_time_series_comparison
from app.agent.tools.workbook_headers import HeaderContext


def test_distant_single_row_tables_do_not_form_a_series() -> None:
    rows = [_row(2, "2024-01-01", 10), _row(30, "2025-01-01", 100)]

    comparison = build_time_series_comparison(rows, _headers(rows), "변화를 알려줘")

    assert comparison is None


def test_distant_tables_with_same_date_column_are_not_one_series() -> None:
    rows = [
        _row(2, "2024-01-01", 10),
        _row(30, "2025-01-01", 100),
        _row(31, "2025-02-01", 120),
    ]

    comparison = build_time_series_comparison(rows, _headers(rows), "변화를 알려줘")

    assert comparison is not None
    assert comparison["start_date"] == "2025-01-01"
    assert comparison["end_date"] == "2025-02-01"
    assert comparison["start_reference"] == "Metrics!A30"
    assert comparison["end_reference"] == "Metrics!A31"
    assert comparison["metrics"] == [
        {
            "header": "Revenue",
            "start_value": 100,
            "end_value": 120,
            "change": 20.0,
            "start_number_format": "General",
            "end_number_format": "General",
            "start_reference": "Metrics!B30",
            "end_reference": "Metrics!B31",
        }
    ]


def test_nearby_rows_with_same_schema_remain_one_series() -> None:
    rows = [_row(2, "2025-01-01", 100), _row(14, "2025-02-01", 120)]

    comparison = build_time_series_comparison(rows, _headers(rows), "변화를 알려줘")

    assert comparison is not None
    assert comparison["start_reference"] == "Metrics!A2"
    assert comparison["end_reference"] == "Metrics!A14"


def test_metric_comparison_preserves_each_endpoint_number_format() -> None:
    rows = [
        _row(2, "2025-01-01", 0.1, "0%"),
        _row(3, "2025-02-01", 0.2, "0.0%"),
    ]

    comparison = build_time_series_comparison(rows, _headers(rows), "변화를 알려줘")

    assert comparison is not None
    assert comparison["metrics"][0]["start_number_format"] == "0%"
    assert comparison["metrics"][0]["end_number_format"] == "0.0%"


@pytest.mark.parametrize("question,start,change", [
    ("처음과 마지막 비교해서 가장 많이 감소한 부서는?", 100, 20),
    ("최고점 대비 마지막 인원이 가장 많이 감소한 부서는?", 200, -80),
])
def test_explicit_endpoints_are_not_silently_replaced_by_a_peak(question, start, change):
    rows = [_row(2, "2024-01-01", 100), _row(3, "2024-02-01", 200),
            _row(4, "2024-03-01", 120)]
    comparison = build_time_series_comparison(rows, _headers(rows), question)
    assert comparison["metrics"][0]["start_value"] == start
    assert comparison["metrics"][0]["change"] == change
    if change > 0:
        assert comparison["ranked_changes"] == []


@pytest.mark.parametrize("date_header", ("Period", "기준월"))
def test_common_period_headers_are_recognized(date_header: str) -> None:
    rows = [_row(2, "2025-01-01", 100), _row(3, "2025-02-01", 120)]
    headers = {
        (row.sheet_name, row.row_number, column): header
        for row in rows
        for column, header in (("A", date_header), ("B", "Revenue"))
    }

    comparison = build_time_series_comparison(rows, headers, "변화를 알려줘")

    assert comparison is not None
    assert comparison["start_date"] == "2025-01-01"


def _row(
    row_number: int, date: str, value: int | float, number_format: str = "General"
) -> IndexedRow:
    return IndexedRow(
        "Metrics",
        row_number,
        (
            IndexedCell("Metrics", f"A{row_number}", date, None),
            IndexedCell(
                "Metrics", f"B{row_number}", value, None,
                number_format=number_format,
            ),
        ),
    )


def _headers(rows: list[IndexedRow]) -> HeaderContext:
    return {
        (row.sheet_name, row.row_number, column): header
        for row in rows
        for column, header in (("A", "Date"), ("B", "Revenue"))
    }
