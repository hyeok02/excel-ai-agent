"""Latest observations preserve date, entity, header, and period bases."""
from app.services.insights.narratives.vertical_latest_narratives import vertical_latest_report
from tests.support.recent_record_fixtures import cell, context


def test_latest_series_sorts_dates_and_reports_percentage_points():
    rows = [[cell("A1", "Year"), cell("B1", "Occupancy rate")],
            [cell("A2", 2025), cell("B2", .8, "0.0%")],
            [cell("A3", 2023), cell("B3", .4, "0.0%")],
            [cell("A4", 2024), cell("B4", .9, "0.0%")]]
    items, overview = vertical_latest_report(context(rows))
    assert len(items) == 1
    assert "2024년 90 %" in overview and "2025년 80 %" in overview
    assert "10%p 감소" in overview
    assert "'Data'!A2" in items[0].evidence and "'Data'!A4" in items[0].evidence


def test_latest_series_does_not_fall_back_to_old_rows_when_latest_missing():
    rows = [[cell("A1", "Year"), cell("B1", "Total")],
            [cell("A2", 2023), cell("B2", 10)], [cell("A3", 2024), cell("B3", 20)],
            [cell("A4", 2025), cell("B4", "#PEND")]]
    assert not vertical_latest_report(context(rows))[0]
    rows[-1][1]["value"] = 30
    rows[-1][0]["value"] = 2024
    assert not vertical_latest_report(context(rows))[0]


def test_non_date_identifier_header_does_not_become_year_axis():
    rows = [[cell("A1", "Policy"), cell("B1", "Total")],
            [cell("A2", 2024), cell("B2", 20)], [cell("A3", 2025), cell("B3", 30)]]
    assert not vertical_latest_report(context(rows))[0]


def test_vertical_series_never_connects_different_entities():
    rows = [[cell("A1", "Year"), cell("B1", "Company"), cell("C1", "Revenue")],
            [cell("A2", 2024), cell("B2", "North"), cell("C2", 100)],
            [cell("A3", 2025), cell("B3", "South"), cell("C3", 1000)]]
    assert not vertical_latest_report(context(rows))[0]


def test_vertical_actual_forecast_titles_are_never_lost():
    rows = [[cell("A1", "Actual")], [cell("A2", "Year"), cell("B2", "Total sales")],
            [cell("A3", 2023), cell("B3", 100)], [cell("A4", 2024), cell("B4", 200)],
            [cell("A10", "Forecast")], [cell("A11", "Year"), cell("B11", "Total sales")],
            [cell("A12", 2025), cell("B12", 500)], [cell("A13", 2026), cell("B13", 1000)]]
    items, overview = vertical_latest_report(context(rows))
    assert len(items) == 2
    forecast = next(item for item in items if "1,000" in item.fact)
    assert "전망" in forecast.fact and "'Data'!A10" in forecast.evidence
    assert any("실적" in item.fact for item in items)


def test_annual_ytd_and_monthly_sections_never_mix():
    rows = [[cell("A1", "(Thousand Megawatthours)")],
            [cell("A2", "Period"), cell("B2", "Natural Gas"), cell("C2", "Total Generation")],
            [cell("A3", "Annual Totals")],
            [cell("A4", 2024), cell("B4", 40), cell("C4", 100)],
            [cell("A5", 2025), cell("B5", 50), cell("C5", 110)],
            [cell("A6", "Year to Date")],
            [cell("A7", 2025), cell("B7", 20), cell("C7", 60)],
            [cell("A8", 2026), cell("B8", 25), cell("C8", 66)],
            [cell("A9", "Year 2026")],
            [cell("A10", "July"), cell("B10", 4), cell("C10", 10)],
            [cell("A11", "August"), cell("B11", 5), cell("C11", 12)]]
    items, overview = vertical_latest_report(context(rows))
    assert len(items) == 3
    assert all("총 발전량" in item.fact for item in items)
    assert "연간 합계" in items[0].fact and "2025년 110 천 MWh" in items[0].fact
    assert "연초 이후 누적" in items[1].fact and "2026년 66 천 MWh" in items[1].fact
    assert "2026년 7월 10" in items[2].fact and "2026년 8월 12" in items[2].fact
    assert all("'Data'!A1" in item.evidence for item in items)


def test_multirow_header_context_is_preserved():
    rows = [[cell("B1", "Adult beds"), cell("D1", "Children beds")],
            [cell("A2", "Month"), cell("B2", "Available"), cell("C2", "Occupied"), cell("D2", "Available")],
            [cell("A3", "November 2025"), cell("B3", 100), cell("C3", 90), cell("D3", 20)],
            [cell("A4", "December 2025"), cell("B4", 110), cell("C4", 88), cell("D4", 30)]]
    items, overview = vertical_latest_report(context(rows))
    assert "성인 병상 · 가용" in overview and "아동 병상 · 가용" in overview
    assert any("'Data'!B1" in item.evidence for item in items)
    assert any("'Data'!D1" in item.evidence for item in items)
