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


def _row(row_number: int, date: str, value: int) -> IndexedRow:
    return IndexedRow(
        "Metrics",
        row_number,
        (
            IndexedCell("Metrics", f"A{row_number}", date, None),
            IndexedCell("Metrics", f"B{row_number}", value, None),
        ),
    )


def _headers(rows: list[IndexedRow]) -> HeaderContext:
    return {
        (row.sheet_name, row.row_number, column): header
        for row in rows
        for column, header in (("A", "Date"), ("B", "Revenue"))
    }
