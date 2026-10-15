"""Small source-shaped contexts shared by diverse Q&A regressions."""


def cell(address, value, number_format="General"):
    return {"cell": address, "value": value, "number_format": number_format}


def sales_context():
    points = [
        ("2025-01-01", "B1", 100, "B2"),
        ("2025-06-01", "C1", 150, "C2"),
    ]
    series = {
        "metric": "Sales", "label_cell": "A2", "scope": None, "basis": None,
        "points": [
            {"period": period, "period_cell": period_cell, "value": value,
             "value_cell": value_cell, "number_format": "$#,##0"}
            for period, period_cell, value, value_cell in points
        ],
    }
    return _context("Sales", horizontal_series=[series])


def plain_record_context():
    values = [
        {"cell": "A2", "label": "상품", "value": "노트북"},
        {"cell": "B2", "label": "1월", "value": 10},
        {"cell": "C2", "label": "2월", "value": 20},
    ]
    return _context(
        "매출현황", selected_records=[{"location": "매출현황!A2:C2", "values": values}]
    )


def checklist_context():
    headers = ("IP", "장비", "작업", "네트워크 안정", "자료 유무")
    records = [
        ("10.0.0.1", "CVD #1", "o", "x", "o"),
        ("10.0.0.2", "CVD #2", "o", "x", "o"),
        ("10.0.0.3", "CVD #3", "o", "o", "o"),
        ("10.0.0.4", "CVD #4", "o", "o", "o"),
        ("10.0.0.5", "CVD #5", "△", "?", "o"),
        ("10.0.0.6", "CVD #6", None, None, None),
        ("10.0.0.7", "CVD #7", None, None, None),
    ]
    rows = [[cell(f"{column}1", value) for column, value in zip("ABCDE", headers)]]
    rows.extend([
        cell(f"{column}{number}", value)
        for column, value in zip("ABCDE", values) if value is not None
    ] for number, values in enumerate(records, start=2))
    return _context(
        "작업현황", table_rows=rows, selected_records=[], numeric_changes=[],
        time_series=[],
    )


def snapshot_context():
    rows = [
        [cell("B63", "Market Cap"), cell("D63", 1_018_667)],
        [cell("B64", "Total Debt"), cell("D64", 67_095)],
        [cell("B68", "TEV"), cell("D68", 1_081_598)],
        [cell("B54", "3 Year Beta"), cell("D54", 0.4354)],
    ]
    return _context("요약", table_regions=[{"title": "VALUATION", "rows": rows}])


def ownership_context():
    rows = [
        [cell("A1", "Rank"), cell("B1", "Name"),
         cell("C1", "Shares Held"), cell("D1", "Share (%)")],
        [cell("A2", 1), cell("B2", "The Vanguard Group"),
         cell("C2", 1_000), cell("D2", 9.44)],
    ]
    return _context(
        "Ownership", table_regions=[{"title": "Top Holders", "rows": rows}]
    )


def event_context():
    values = [
        {"cell": "A2", "label": "Announced Date", "value": "2025-01-03"},
        {"cell": "B2", "label": "Event Type", "value": "Strategic Investment"},
        {"cell": "C2", "label": "Headline", "value": (
            "Riot Games announced a major strategic investment "
            "in its publishing operations."
        )},
    ]
    return _context(
        "Events", selected_records=[{"location": "Events!A2:C2", "values": values}]
    )


def _context(name, **facts):
    return {"sheets": [{"name": name, "business_facts": facts}]}
