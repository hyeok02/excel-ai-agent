from app.services.insights.snapshot_narratives import snapshot_report


def cell(address, value, number_format=None):
    return {"cell": address, "value": value, "number_format": number_format}


def context(rows, title=None):
    return {"sheets": [{"name": "요약", "business_facts": {
        "table_regions": [{"title": title, "rows": rows}],
    }}]}


FIGURES = [
    [cell("B63", "Market Cap"), cell("D63", 1018667)],
    [cell("B64", "Total Debt"), cell("D64", 67095)],
    [cell("B68", "TEV"), cell("D68", 1081598)],
    [cell("B54", "3 Year Beta"), cell("D54", 0.4354)],
]


def test_reports_current_levels_largest_first() -> None:
    items, overview = snapshot_report(context(FIGURES, "VALUATION"))
    assert items
    assert items[0].fact.startswith(
        "VALUATION의 주요 수치는 시가총액(Market Cap) 1,018,667, 기업가치(TEV) 1,081,598"
    )
    assert (items[0].fact.index("총부채(Total Debt) 67,095")
            < items[0].fact.index("3 Year Beta"))
    assert overview == items[0].fact


def test_ratios_are_reported_apart_from_measured_figures() -> None:
    rows = [*FIGURES,
            [cell("J76", "Total Debt/EBITDA"), cell("L76", 1.407)],
            [cell("J77", "Net Debt/EBITDA"), cell("L77", 1.182)]]
    items, _ = snapshot_report(context(rows))
    assert "Total Debt/EBITDA" not in items[0].fact
    assert items[1].title == "비율 지표"
    assert "Total Debt/EBITDA 1.41" in items[1].fact
    assert "비율 지표" == items[1].title


def test_a_dated_series_is_left_to_the_trend_narratives() -> None:
    rows = [[cell("B1", "항목"), cell("C1", "2024-01-31"), cell("D1", "2025-01-31")],
            *FIGURES]
    assert snapshot_report(context(rows)) == ([], "")


def test_too_few_figures_report_nothing() -> None:
    assert snapshot_report(context(FIGURES[:2])) == ([], "")
