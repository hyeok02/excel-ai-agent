from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.tools.workbook_comparisons import build_time_series_comparison


COLUMNS = {
    "G": ("Department", "General & Administrative"),
    "N": ("Department", "Research & Development"),
    "R": ("Department", "Sales & Marketing"),
    "W": ("Department", "Services"),
    "AH": ("Department", "Other"),
}


def test_department_decrease_excludes_total_and_role_columns() -> None:
    rows = [
        _header_row(106, 0),
        _header_row(107, 1),
        _data_row(108, "2025-06-01", 4000, 10, [904, 1816, 385, 1081, 1231]),
        _data_row(115, "2023-09-01", 6000, 1000, [1018, 1959, 461, 1277, 1386]),
    ]
    headers = {
        ("Metrics", row, column): path[-1]
        for row in (108, 115)
        for column, path in COLUMNS.items()
    }
    headers.update({("Metrics", row, "E"): "Date" for row in (108, 115)})
    headers.update({("Metrics", row, "F"): "Total Employees" for row in (108, 115)})
    headers.update({("Metrics", row, "H"): "Legal" for row in (108, 115)})

    comparison = build_time_series_comparison(
        rows, headers, "제일 많이 감소한 부서는?", "department", {"Metrics": COLUMNS}
    )

    assert comparison is not None
    assert comparison["start_date"] == "2023-09-01"
    assert comparison["end_date"] == "2025-06-01"
    assert [item["header"] for item in comparison["metrics"]] == [
        path[-1] for path in COLUMNS.values()
    ]
    assert comparison["ranked_changes"][0] == {
        "header": "Services",
        "start_value": 1277,
        "end_value": 1081,
        "change": -196.0,
        "header_references": ["Metrics!W106", "Metrics!W107"],
        "start_reference": "Metrics!W115",
        "end_reference": "Metrics!W108",
    }


def test_explicit_period_limits_both_comparison_endpoints() -> None:
    rows = [
        _header_row(106, 0), _header_row(107, 1),
        _data_row(108, "2025-06-01", 4000, 10, [904, 1816, 385, 1081, 1231]),
        _data_row(110, "2024-12-01", 4200, 12, [914, 1815, 389, 1075, 1235]),
        _data_row(114, "2023-12-01", 5000, 15, [1016, 1961, 458, 1244, 1340]),
        _data_row(115, "2023-09-01", 6000, 20, [1018, 1959, 461, 1277, 1386]),
    ]
    data_rows = (108, 110, 114, 115)
    headers = {
        ("Metrics", row, column): path[-1]
        for row in data_rows for column, path in COLUMNS.items()
    }
    headers.update({("Metrics", row, "E"): "Date" for row in data_rows})

    comparison = build_time_series_comparison(
        rows, headers, "2023년 12월부터 2024년 12월까지 가장 감소한 부서는?",
        "department", {"Metrics": COLUMNS},
    )

    assert comparison is not None
    assert comparison["start_date"] == "2023-12-01"
    assert comparison["end_date"] == "2024-12-01"


def _header_row(row_number: int, level: int) -> IndexedRow:
    return IndexedRow(
        "Metrics",
        row_number,
        tuple(
            IndexedCell("Metrics", f"{column}{row_number}", labels[level], None)
            for column, labels in COLUMNS.items()
        ),
    )


def _data_row(
    row_number: int, day: str, total: int, legal: int, departments: list[int]
) -> IndexedRow:
    cells = [
        IndexedCell("Metrics", f"E{row_number}", day, None),
        IndexedCell("Metrics", f"F{row_number}", total, None),
        IndexedCell("Metrics", f"H{row_number}", legal, None),
    ]
    cells.extend(
        IndexedCell("Metrics", f"{column}{row_number}", value, None)
        for column, value in zip(COLUMNS, departments)
    )
    return IndexedRow("Metrics", row_number, tuple(cells))
