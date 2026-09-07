"""Small source-shaped fixtures for meaningful, provenance-preserving summaries."""


def trend_context(metrics=("전체 인원", "기획 부문", "운영 부문"), unit=None):
    dates = ["2025-01-01", "2025-02-01", "2025-03-01"]
    points = [(1000, 600, 400), (950, 590, 360), (900, 585, 315)]
    identity = {
        "location": "현황!A1:B1",
        "values": [{"cell": "A1", "value": "분석 대상"},
                   {"cell": "B1", "value": "푸른연구원"}],
    }
    rows = []
    for row, (date, amounts) in enumerate(zip(dates, points), start=4):
        values = [{"cell": f"A{row}", "label": "기준일", "value": date}]
        values.extend(
            {"cell": f"{column}{row}", "label": metric, "value": value,
             "number_format": f'#,##0"{unit}"' if unit else "#,##0"}
            for column, metric, value in zip("BCD", metrics, amounts)
        )
        rows.append({"location": f"현황!A{row}:D{row}", "values": values})
    changes = [
        {
            "metric": metric, "earliest_period": dates[0], "latest_period": dates[-1],
            "earliest_value": points[0][index], "latest_value": points[-1][index],
            "change": points[-1][index] - points[0][index],
            "change_rate_percent": round(
                (points[-1][index] - points[0][index]) / points[0][index] * 100, 2,
            ),
            "evidence": [rows[0]["location"], rows[-1]["location"]],
        }
        for index, metric in enumerate(metrics)
    ]
    return {
        "filename": "synthetic-summary.xlsx", "omitted_sheet_count": 0,
        "sheets": [{"name": "현황", "business_facts": {
            "selected_records": [identity, *rows], "numeric_changes": changes,
        }}],
    }


def source_records(context):
    return context["sheets"][0]["business_facts"]["selected_records"]
