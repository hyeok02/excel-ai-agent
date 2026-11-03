"""Annual, grouped and formatted axes retain their source meaning."""
from itertools import permutations

import pytest

from app.services.insights.facts.fact_trends import date_value
from app.services.insights.facts.horizontal_series import extract_horizontal_series
from app.services.insights.narratives.horizontal_trends import horizontal_trend_report
from app.services.insights.narratives.table_narratives import table_report
from app.services.insights.display.display_quality import business_priority, metric_family
from tests.test_horizontal_series import cell, region


def report(source):
    series = extract_horizontal_series([source])
    return series, horizontal_trend_report({"sheets": [{
        "name": "Measurements", "business_facts": {"horizontal_series": series},
    }]})


@pytest.mark.parametrize("order", list(permutations(range(3))))
def test_contextual_annual_axis_is_permutation_invariant_and_scales_percent(order):
    years, values = (2018, 2019, 2020), (.12, .08, .09)
    source = region(
        [cell("A1", "Sensor availability, 2018–2020")],
        [cell("A2", "Metric"), *[cell(f"{chr(66 + position)}2", years[index])
                                 for position, index in enumerate(order)]],
        [cell("A3", "Sensor Z"), *[cell(f"{chr(66 + position)}3", values[index], "0.0%")
                                   for position, index in enumerate(order)]],
    )
    [series], ([item], overview) = report(source)
    assert len(series["observations"]) == 3
    assert "2018년 12.0%에서 2020년 9.0%" in overview
    assert "2019년 8.0%에서 2020년 9.0%" in overview
    assert "감소한 뒤 반등" in overview
    assert "최근 구간" in overview
    assert all(f"'Measurements'!{column}3" in item.evidence for column in "BCD")
    assert date_value("2018") is None  # General numeric cells remain non-dates.


def test_quantity_or_identifier_row_does_not_become_an_annual_axis():
    source = region([cell("A1", "Product"), cell("B1", 2018), cell("C1", 2019), cell("D1", 2020)],
                    [cell("A2", "Units sold"), cell("B2", 12), cell("C2", 8), cell("D2", 9)])
    assert extract_horizontal_series([source]) == []


def test_annual_series_allows_unavailable_edges_but_never_an_internal_gap():
    source = region([cell("A1", "Year"), *[cell(f"{column}1", year)
                                            for column, year in zip("BCDEF", range(2016, 2021))]],
                    [cell("A2", "Gauge Q"), cell("B2", "-"), cell("C2", "-"),
                     cell("D2", .12, "0.0%"), cell("E2", .08, "0.0%"), cell("F2", .09, "0.0%")])
    [series], ([item], _) = report(source)
    assert series["axis_period_count"] == 5
    assert [point["period_label"] for point in series["observations"]] == ["2018년", "2019년", "2020년"]
    assert "2016년" not in item.fact and "2018년 12.0%" in item.fact
    source["analysis_rows"][1][4]["value"] = "-"
    assert extract_horizontal_series([source]) == []


def test_parent_metric_and_rate_unit_stay_with_each_reversed_date_group():
    source = region(
        [cell("A1", "Energy prices (Cents per Kilowatthour)")],
        [cell("B2", "Domestic"), cell("D2", "Enterprise")],
        [cell("B3", "August 2026"), cell("C3", "August 2025"),
         cell("D3", "August 2026"), cell("E3", "August 2025")],
        [cell("A4", "West District"), cell("B4", 28.31), cell("C4", 29.01),
         cell("D4", 20.5), cell("E4", 19.5)],
    )
    series, (items, overview) = report(source)
    assert len(series) == len(items) == 2
    domestic = next(item for item in items if "Domestic" in item.title)
    enterprise = next(item for item in items if "Enterprise" in item.title)
    assert "2025년 8월 29.01 센트/kWh에서 2026년 8월 28.31" in domestic.fact
    assert "감소" in domestic.fact and "증가" in enterprise.fact
    assert "'Measurements'!B2" in domestic.evidence and "'Measurements'!A1" in domestic.evidence
    assert "'Measurements'!D4" not in domestic.evidence


def test_table_axis_keeps_latest_period_beyond_seven_columns_and_formats_values():
    headers = [{"cell": f"{chr(66 + index)}1", "value": f"2025-{month:02d}-01"}
               for index, month in enumerate(range(9, 0, -1))]
    values = [{"cell": f"{chr(66 + index)}2", "value": month / 100, "number_format": "0.0%"}
              for index, month in enumerate(range(9, 0, -1))]
    rows = [headers, [{"cell": "A2", "value": "Yield"}, *values]]
    items, overview = table_report({"sheets": [{"name": "Measurements", "business_facts": {
        "table_regions": [{"rows": rows}],
    }}]})
    assert "2025년 1월 1일부터 2025년 9월 1일까지 9개" in overview
    assert "1%~9%" in items[0].fact
    assert "'Measurements'!B2" in items[0].evidence


def test_table_report_does_not_choose_one_of_repeated_parent_date_groups():
    rows = [
        [{"cell": "B1", "value": "North"}, {"cell": "D1", "value": "South"}],
        [{"cell": f"{column}2", "value": value} for column, value in
         zip("BCDE", ["2024-01-01", "2025-01-01"] * 2)],
        [{"cell": "A3", "value": "Volume"}, *[
            {"cell": f"{column}3", "value": value} for column, value in zip("BCDE", [10, 20, 30, 40])]],
    ]
    assert table_report({"sheets": [{"name": "Measurements", "business_facts": {
        "table_regions": [{"rows": rows}],
    }}]}) == ([], "")


def test_descriptive_label_is_used_instead_of_code_and_all_dimensions_are_cited():
    source = region(
        [cell("A1", "Code"), cell("B1", "Name"), cell("C1", "Geography"),
         cell("D1", "Mid-2024"), cell("E1", "Mid-2023")],
        [cell("A2", "ZX123456"), cell("B2", "Island District"), cell("C2", "Region"),
         cell("D2", 120), cell("E2", 100)],
    )
    [series], ([item], _) = report(source)
    assert series["metric"] == "Island District"
    assert "ZX123456" not in item.fact and "Island District" in item.fact
    assert "'Measurements'!B2" in item.evidence


def test_explicit_total_is_retained_before_horizontal_series_cap():
    source = region([cell("B1", "2024-01-01"), cell("C1", "2025-01-01")], *[
        [cell(f"A{row}", f"Group {row}"), cell(f"B{row}", 10), cell(f"C{row}", 20)]
        for row in range(2, 40)
    ], [cell("A40", "Grand Total"), cell("B40", 380), cell("C40", 760)])
    series, (items, _) = report(source)
    assert len(series) == 24 and series[0]["metric"] == "Grand Total"
    assert items[0].title == "총합계 변화"


@pytest.mark.parametrize("label", ["Lancashire", "Cashmere County", "Profitopolis"])
def test_entity_names_do_not_acquire_metric_families_from_english_substrings(label):
    assert business_priority(label) == 0
    assert metric_family(label) == ""


@pytest.mark.parametrize("label,family", [
    ("TotalRevenue", "revenue"), ("Total_Employees", "headcount"),
    ("Cash Flow", "cash"), ("영업이익률", "ebit"),
])
def test_source_metric_compounds_remain_recognized(label, family):
    assert business_priority(label) > 0
    assert metric_family(label) == family
