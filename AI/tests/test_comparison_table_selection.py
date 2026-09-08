from app.agent.query.comparison_scope import requested_change_direction
from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.tools.workbook_comparisons import build_time_series_comparison


def test_longer_unrelated_table_does_not_hide_scoped_table() -> None:
    rows = [
        _row(2, "2024-01-01", 100),
        _row(3, "2024-02-01", 90),
        _row(4, "2024-03-01", 80),
        _header(8, "Department"),
        _header(9, "Services"),
        _row(10, "2024-01-01", 1277),
        _row(11, "2025-01-01", 1081),
    ]
    headers = {
        ("Metrics", row, "E"): "Date" for row in (2, 3, 4, 10, 11)
    }
    headers.update({("Metrics", row, "G"): "Revenue" for row in (2, 3, 4)})
    headers.update({("Metrics", row, "G"): "Services" for row in (10, 11)})

    comparison = build_time_series_comparison(
        rows,
        headers,
        "가장 많이 감소한 부서는?",
        "department",
        {"Metrics": {"G": ("Department", "Services")}},
    )

    assert comparison is not None
    assert comparison["start_reference"] == "Metrics!E10"
    assert comparison["end_reference"] == "Metrics!E11"
    assert comparison["ranked_changes"][0]["header"] == "Services"


def test_mixed_increase_and_decrease_question_is_not_forced_one_way() -> None:
    assert requested_change_direction("가장 많이 증가한 부서와 감소한 부서는?") is None


def _row(row_number: int, day: str, value: int) -> IndexedRow:
    return IndexedRow(
        "Metrics",
        row_number,
        (
            IndexedCell("Metrics", f"E{row_number}", day, None),
            IndexedCell("Metrics", f"G{row_number}", value, None),
        ),
    )


def _header(row_number: int, value: str) -> IndexedRow:
    return IndexedRow(
        "Metrics",
        row_number,
        (IndexedCell("Metrics", f"G{row_number}", value, None),),
    )
