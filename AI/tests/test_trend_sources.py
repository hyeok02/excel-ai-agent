"""Source extractor retains complete dated records and fails on missing axes."""
from dataclasses import replace
from datetime import datetime
from io import BytesIO

import pytest
from openpyxl import Workbook

from app.agent.query.index import build_workbook_data_index
from app.agent.query.trend_sources import trend_candidates
from app.services.workbook_parser import parse_workbook


def _fixture(rows):
    book = Workbook()
    book.active.title = "History"
    for row in rows:
        book.active.append(row)
    stream = BytesIO()
    book.save(stream)
    content = stream.getvalue()
    return parse_workbook("history.xlsx", content), build_workbook_data_index("history.xlsx", content)


def test_reverse_vertical_preserves_every_observation_and_evidence():
    summary, index = _fixture([
        ["Date", "Total Employees"],
        [datetime(2026, 3, 1), 14], [datetime(2026, 1, 1), 12], [datetime(2026, 2, 1), 10],
    ])
    candidates = trend_candidates(summary, index, "전체 직원 수의 기간별 추이를 설명해줘")
    valid = [candidate for candidate in candidates if not candidate.error]
    assert len(valid) == 1
    assert [item.value.value for item in valid[0].observations] == [14, 12, 10]
    assert valid[0].observations[0].period_cell.address == "A2"
    assert valid[0].observations[0].label.address == "B1"


@pytest.mark.parametrize("date,value,reason", [
    (None, 10, "missing_or_invalid_value"),
    ("not a date", 10, "missing_or_invalid_date"),
    (datetime(2026, 2, 1), None, "missing_or_invalid_value"),
    (datetime(2026, 2, 1), "N/A", "missing_or_invalid_value"),
    (datetime(2026, 2, 1), "=EXTERNAL()", "missing_or_invalid_value"),
])
def test_bad_middle_period_never_disappears(date, value, reason):
    summary, index = _fixture([["Date", "Amount"],
                               [datetime(2026, 1, 1), 12], [date, value], [datetime(2026, 3, 1), 14]])
    candidates = trend_candidates(summary, index, "Amount trend")
    assert candidates and not any(not candidate.error for candidate in candidates)
    assert reason in {candidate.error for candidate in candidates}


def test_unqualified_series_cannot_mix_entity_rows():
    summary, index = _fixture([["Date", "Amount", "Company"],
                               [datetime(2026, 1, 1), 12, "Alpha Systems"],
                               [datetime(2026, 2, 1), 10, "Beta Systems"],
                               [datetime(2026, 3, 1), 14, "Alpha Systems"]])
    candidates = trend_candidates(summary, index, "Amount trend")
    assert candidates and all(candidate.error == "ambiguous_entity_scope" for candidate in candidates)
    selected = trend_candidates(summary, index, "Alpha Systems Amount trend")
    assert [item.value.value for item in selected[0].observations] == [12, 14]


def test_partial_source_cannot_certify_a_prefix():
    summary, index = _fixture([["Date", "Amount"], ["2025-01-01", 1], ["2025-02-01", 2]])
    index = replace(index, rows=index.rows[:2], truncated=True, truncated_sheet_names=frozenset({"History"}))
    candidates = trend_candidates(summary, index, "Amount trend")
    assert candidates and all(candidate.error for candidate in candidates)


def test_horizontal_period_columns_are_not_ordered_by_position():
    summary, index = _fixture([["Metric", "2025-03-01", "2025-01-01", "2025-02-01"],
                               ["Revenue", 140, 120, 100]])
    candidates = trend_candidates(summary, index, "Revenue trend")
    valid = [candidate for candidate in candidates if not candidate.error]
    assert len(valid) == 1
    assert [item.period.month for item in valid[0].observations] == [3, 1, 2]
    assert [item.value.address for item in valid[0].observations] == ["B2", "C2", "D2"]


@pytest.mark.parametrize("middle", [None, "N/A", "=EXTERNAL()"])
def test_horizontal_missing_middle_value_cannot_be_omitted(middle):
    summary, index = _fixture([["Metric", "2025-01-01", "2025-02-01", "2025-03-01"],
                               ["Revenue", 120, middle, 140]])
    candidates = trend_candidates(summary, index, "Revenue trend")
    assert candidates and all(candidate.error for candidate in candidates)


def test_horizontal_invalid_final_text_is_not_a_new_metric_boundary():
    summary, index = _fixture([["Metric", "2025-01-01", "2025-02-01", "2025-03-01"],
                               ["Revenue", 120, 140, "unavailable"]])
    candidates = trend_candidates(summary, index, "Revenue trend")
    assert candidates and all(candidate.error for candidate in candidates)


def test_two_horizontal_date_axes_cannot_choose_the_closest_arbitrarily():
    summary, index = _fixture([["Observation Date", "2024-01-01", "2024-02-01", "2024-03-01"],
                               ["Effective Date", "2023-03-01", "2023-01-01", "2023-02-01"],
                               ["Revenue", 120, 140, 130]])
    candidates = trend_candidates(summary, index, "Revenue trend")
    assert candidates and all(candidate.error for candidate in candidates)


def test_numeric_product_and_department_columns_are_measures_not_entity_keys():
    summary, index = _fixture([["Date", "Total Employees", "Product", "Department", "Region"],
                               ["2025-01-01", 120, 40, 12, 3],
                               ["2025-02-01", 140, 50, 14, 4]])
    candidates = trend_candidates(summary, index, "전체 직원 수의 기간별 추이를 설명해줘")
    assert len(candidates) == 1 and candidates[0].error is None
    assert [point.value.value for point in candidates[0].observations] == [120, 140]


@pytest.mark.parametrize("matrix", [
    [["Date", "Revenue", "Total Employees"], ["2025-01-01", 120, 10], ["2025-02-01", 140, 20]],
    [["Metric", "2025-01-01", "2025-02-01"], ["Revenue", 120, 140], ["Total Employees", 10, 20]],
])
def test_translated_metric_uses_actual_revenue_source_not_other_numeric_measure(matrix):
    summary, index = _fixture(matrix)
    candidates = trend_candidates(summary, index, "매출의 기간별 추이를 설명해줘")
    valid = [candidate for candidate in candidates if not candidate.error]
    assert len(valid) == 1
    assert {point.label.value for point in valid[0].observations} == {"Revenue"}
    assert [point.value.value for point in valid[0].observations] == [120, 140]
