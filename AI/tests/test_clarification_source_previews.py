"""Source choices expose values without presenting sample rows as an answer."""
from dataclasses import replace

from app.agent.query.ambiguity_tables import candidates_for
from app.agent.query.clarification_options import source_clarification_options
from app.agent.query.tabular_catalog import build_query_tables
from tests.tabular_query_fixtures import table_fixture


def choices(matrix, question="현재 직원 수 몇 명이야?", complete=True):
    summary, index = table_fixture([(1, 1, matrix)], complete=complete)
    table = build_query_tables(summary)[0]
    column = next(column for column in table.columns if "Headcount" in column.header)
    return candidates_for(question, [(table, column)], index), summary, index, table, column


def test_latest_preview_contains_real_value_date_entity_unit_and_source_cells():
    result, summary, index, _, _ = choices([
        ["Date", "Company", "Headcount"],
        ["2024-12-31", "Alpha Co", 100], ["2025-12-31", "Alpha Co", 120],
    ])
    assert len(result) == 1
    details = result[0].details
    assert "120명" in details and "2025-12-31" in details and "Alpha Co" in details
    assert "100명" not in details and "2024-12-31" not in details
    assert "집계 결과 아님" in details
    assert {"A3", "B3", "C3"} <= {cell.address for cell in result[0].cells}
    options = source_clarification_options("현재 직원 수 몇 명이야?", result, summary, index)
    assert len(options) == 1 and options[0].details == details


def test_missing_date_is_disclosed_not_inferred_from_filename_or_latest_label():
    result, *_ = choices([["Company", "Headcount (Latest)"], ["Alpha Co", 120]])
    assert "120명" in result[0].details and "기준일 미확인" in result[0].details
    assert "현재 값으로 확정하지 않았습니다" in result[0].details


def test_multiple_entities_are_not_reduced_to_company_with_newest_date():
    result, *_ = choices([
        ["Date", "Company", "Headcount"],
        ["2024-12-31", "Alpha Co", 100], ["2025-12-31", "Beta Co", 120],
    ])
    # Latest-row previews must not conceal a genuinely competing population.
    assert "Alpha Co" in result[0].details and "Beta Co" in result[0].details


def test_zero_is_a_real_source_value_not_a_missing_preview():
    result, *_ = choices([["Company", "Headcount"], ["Alpha Co", 0]])
    assert len(result) == 1 and "값: 0명" in result[0].details


def test_partial_index_does_not_claim_sample_is_latest_or_prove_no_data():
    result, summary, index, table, column = choices([
        ["Date", "Company", "Headcount"], ["2024-12-31", "Alpha Co", 100],
    ])
    incomplete = replace(index, truncated=True)
    result = candidates_for("현재 직원 수 몇 명이야?", [(table, column)], incomplete)
    assert len(result) == 1 and "예시" in result[0].details
    assert "최신 값 미확인" in result[0].details


def test_unknown_unit_and_real_context_are_disclosed():
    summary, index = table_fixture([(1, 1, [["Entity", "Amount"], ["Example", 12]])])
    table = build_query_tables(summary)[0]
    result = candidates_for("Amount 합계?", [(table, table.columns[1])], index)
    assert "값: 12" in result[0].details and "단위 미확인" in result[0].details
    assert "Entity: Example" in result[0].details


def test_metric_choices_include_the_actual_value_as_well_as_period_and_unit():
    from app.agent.query.ambiguity_metrics import metric_candidates
    from tests.test_metric_observation_answers import _index, _report
    result = metric_candidates("2024년 9월 30일 Operating Income은?", _index({"Results": _report()}))
    assert len(result) == 2
    assert "650백만 미국 달러" in result[0].details and "회계연도" in result[0].details
    assert "180백만 미국 달러" in result[1].details and "분기" in result[1].details


def test_invalid_tail_date_never_makes_older_examples_look_like_current_values():
    result, *_ = choices([["Dates", "Company", "Headcount"],
                         ["2025-03-31", "Alpha Co", 120], ["#PEND", "Alpha Co", 150]])
    assert len(result) == 1
    assert result[0].details.startswith("최신 값 미확인")
    assert "현재 값으로 확정하지 않았습니다" in result[0].details


def test_plural_dates_header_binds_actual_latest_period():
    result, *_ = choices([["Dates", "Company", "Headcount"],
                         ["2024-12-31", "Alpha Co", 100], ["2025-12-31", "Alpha Co", 120]])
    assert "2025-12-31" in result[0].details and "120명" in result[0].details
    assert "100명" not in result[0].details and "기준일 미확인" not in result[0].details
