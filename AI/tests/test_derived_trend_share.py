"""Explicit share operands must agree in date, scope and unit."""
from dataclasses import replace

import pytest

from app.agent.query.derived_trend_answers import derived_trend_answer
from tests.support.large_workbook_fixtures import offline
from tests.support.trend_scoped_fixtures import formats, refused
from tests.tabular_query_fixtures import table_fixture

QUESTION = "Total Employees 중 Temporary Employees의 비중 추이를 설명해줘"


def _source(rows=None, *, layout="vertical"):
    rows = rows or [["2024-01-31", 100, 20], ["2024-02-29", 150, 15], ["2024-03-31", 120, 30]]
    matrix = [["Date", "Total Employees", "Temporary Employees"], *rows]
    if layout == "horizontal":
        matrix = [["Metric", *[row[0] for row in rows]], ["Total Employees", *[row[1] for row in rows]],
                  ["Temporary Employees", *[row[2] for row in rows]]]
    return table_fixture([(1, 1, matrix)])


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
@pytest.mark.parametrize("question", [QUESTION, "Temporary Employees / Total Employees 비율 추이를 설명해줘",
    "Total Employees 대비 Temporary Employees 비율 추이를 설명해줘",
    "Temporary Employees의 Total Employees 대비 비중 추이를 설명해줘",
    "Temporary Employees as a share of Total Employees trend"])
def test_named_part_and_total_show_same_share_and_full_original_lineage(layout, question):
    summary, index = _source(layout=layout)
    answer = derived_trend_answer(question, summary, index)
    assert answer.status == "answered", answer.model_dump()
    assert answer.verification.level == "request_checked"
    assert "Temporary Employees / Total Employees 비율" in answer.answer
    assert "20% → 25%, 5%p 증가" in answer.answer and "하락 뒤 반등" in answer.answer
    originals = {cell.address: cell.value for row in index.rows for cell in row.cells}
    assert all(originals[item.reference] == item.value for item in answer.evidence)
    assert {20, 15, 30, 100, 150, 120} <= {item.value for item in answer.evidence}


@pytest.mark.parametrize("bad", [None, "missing", 0, -10])
def test_bad_denominator_blocks_entire_share_not_just_that_period(bad):
    summary, index = _source([["2024-01-31", 100, 20], ["2024-02-29", bad, 15], ["2024-03-31", 120, 30]])
    refused(derived_trend_answer(QUESTION, summary, index))


def test_component_above_total_is_not_certified_but_explicit_ratio_is_supported():
    summary, index = _source([["2024-01-31", 10, 20], ["2024-02-29", 10, 15], ["2024-03-31", 12, 30]])
    refused(derived_trend_answer(QUESTION, summary, index))
    answer = derived_trend_answer("Temporary Employees / Total Employees 비율 추이를 설명해줘", summary, index)
    assert answer.status == "answered" and "200% → 250%" in answer.answer


def test_unit_mismatch_and_hidden_population_cannot_be_green():
    summary, index = _source()
    index = formats(summary, index, {"C2": "0%", "C3": "0%", "C4": "0%"})
    refused(derived_trend_answer(QUESTION, summary, index))


@pytest.mark.parametrize("question", [
    "Total Employees와 Temporary Employees의 비율 추이를 설명해줘",
    "Total Employees 비중 추이를 설명해줘",
    QUESTION + " 그리고 UnknownMetric도", QUESTION + " 서울만", QUESTION + " 평균도",
    QUESTION + " 전년 동기 대비 증감률도",
])
def test_ambiguous_order_missing_operand_or_extra_unfulfilled_request_not_certified(question):
    summary, index = _source()
    refused(derived_trend_answer(question, summary, index))


def test_cross_table_missing_dates_never_intersection_joined():
    summary, index = table_fixture([
        (1, 1, [["Date", "Total Employees"], ["2024-01-31", 100], ["2024-02-29", 120], ["2024-03-31", 130]]),
        (7, 1, [["Date", "Temporary Employees"], ["2024-01-31", 20], ["2024-03-31", 30]])])
    refused(derived_trend_answer(QUESTION, summary, index))


def test_truncated_original_and_summary_source_tampering_remain_blocked():
    summary, index = _source()
    shortened = replace(index, rows=index.rows[:-1], truncated=True, truncated_sheet_names=frozenset({"Arbitrary"}))
    refused(derived_trend_answer(QUESTION, summary, shortened))
    for row in summary.sheets[0].regions[0].analysis_rows:
        for cell in row:
            if cell["address"] == "C3":
                cell["value"] = 99
    refused(derived_trend_answer(QUESTION, summary, index))


def test_share_window_ignores_invalid_values_only_after_original_date_binding():
    summary, index = _source([["2023-12-31", None, None], ["2024-01-31", 100, 20],
                             ["2024-02-29", 100, 30], ["2025-01-31", 100, None]])
    answer = derived_trend_answer("2024년 " + QUESTION, summary, index)
    assert answer.status == "answered", answer.model_dump()
    assert "20% → 30%" in answer.answer
