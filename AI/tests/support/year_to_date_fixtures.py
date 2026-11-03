"""Calendar-year monthly records and their matching YTD series."""
from app.services.insights.narratives.vertical_latest_narratives import _series
from app.services.insights.narratives.year_to_date_scope import year_to_date_scope


def _cell(address, value, fmt="General"):
    return {"cell": address, "value": value, "number_format": fmt}


def _fixture(month_count=5):
    import calendar
    rows = [[_cell("A1", "Period"), _cell("B1", "Total output")]]
    totals = []
    for year, scale in [(2023, 1), (2024, 2), (2025, 3)]:
        rows.append([_cell(f"A{len(rows) + 1}", f"Year {year}")])
        values = []
        for month in range(1, month_count + 1):
            row = len(rows) + 1
            value = scale * month
            rows.append([_cell(f"A{row}", calendar.month_name[month]), _cell(f"B{row}", value)])
            values.append(value)
        totals.append((year, sum(values)))
    rows.append([_cell(f"A{len(rows) + 1}", "Year to Date")])
    for year, value in totals:
        row = len(rows) + 1
        rows.append([_cell(f"A{row}", year), _cell(f"B{row}", value)])
    sheet = {"name": "Observations", "business_facts": {"table_regions": [
        {"rows": rows, "rows_complete": True},
    ]}}
    series = list(_series(sheet))
    target = next(entry for entry in series if entry[1] == "Year to Date")
    return sheet, series, target


def _scope(fixture):
    sheet, series, target = fixture
    return year_to_date_scope(sheet, target[1], 2, target[3], series=series)
