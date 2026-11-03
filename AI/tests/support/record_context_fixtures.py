"""Source-linked business descriptions and transaction dates for record tests."""
from tests.support.record_summary_fixtures import _cell, _rows, _source


def _records(name="BookSales", date_header="Date", dates=None):
    source = _source()
    source["filename"] = "irrelevant_insurance_forecast.xlsx"
    source["sheets"][0]["name"] = name
    rows = _rows(source)
    rows[0].append(_cell("F1", date_header))
    dates = dates or ["2024-03-04", "2023-11-19", "2024-01-08",
                      "2024-06-12", "2023-12-25", "2024-02-18"]
    for i, (row, date) in enumerate(zip(rows[1:], dates), 2):
        row.append(_cell(f"F{i}", date, "yyyy-mm-dd"))
    return source


def _notes(source, *texts):
    rows = [[_cell(f"C{i}", text)] for i, text in enumerate(texts, 2)]
    source["sheets"].append({
        "name": "Guide",
        "business_facts": {"table_regions": [{"rows": rows, "rows_complete": True}]},
    })


def _metric(items, topic="TotalPrice"):
    return next(item for item in items if item.category == "metric" and item.topic == topic)
