"""Arbitrary ranked/share tables, independent of customer workbook names."""
from app.services.insights.narratives.ranked_narratives import ranked_report


def context(values, headers=("Rank", "Name", "Quantity", "Share (%)"), complete=True):
    rows = [[{"cell": f"{chr(65 + column)}{row}", "value": value}
             for column, value in enumerate(items) if value is not None]
            for row, items in enumerate([headers, *values], 1)]
    return {"sheets": [{"name": "Data", "business_facts": {
        "table_regions": [{"rows": rows, "rows_complete": complete}],
    }}]}


def interpretations(data):
    insights, _ = ranked_report(data)
    return [item for item in insights if "비중 차이" in item.title
            or "개 항목의 비중 합계" in item.title]


RANKED = [(3, "Gamma", 100, 10), (1, "Alpha", 500, 50), (2, "Beta", 300, 30)]
