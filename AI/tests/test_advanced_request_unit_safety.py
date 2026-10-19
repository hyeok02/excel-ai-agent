"""HAVING compares source-storage units, not merely numerically equal tokens."""
import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan, TabularAggregateCondition, TabularFilter
from app.agent.query.tabular_request_scope import request_matches_plan
from tests.tabular_query_fixtures import table_fixture


def run(question, header, threshold, *, filters=(), statistic="sum", number_format=None, context=None):
    from dataclasses import replace

    summary, _ = table_fixture([(1, 1, [["부서", header, "상태"],
                                       ["Alpha", 120, "Total"], ["Beta", 80, "Average"]])])
    table = build_query_tables(summary)[0]
    if number_format:
        table = replace(table, rows=tuple(replace(row, number_formats={"B": number_format}) for row in table.rows))
    if context is not None:
        table = replace(table, context=context)
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"],
                            group_by=["A"], statistic=statistic, filters=list(filters),
                            having=[TabularAggregateCondition(column_id="B", operator="greater_than", value=threshold)])
    return request_matches_plan(question, plan, table, [table], streaming=True)


def test_won_threshold_must_be_converted_to_stored_million_won_units():
    question = "부서별 매출 합계가 1억원 초과인 그룹"
    assert run(question, "매출(백만원)", 100)
    assert not run(question, "매출(백만원)", 100000000)
    assert not run(question, "매출(백만원)", 1)


def test_compound_quantity_applies_man_to_the_entire_preceding_small_unit_group():
    question = "부서별 매출 합계가 1천3백만원 초과인 그룹"
    assert run(question, "매출(원)", 13000000)
    assert not run(question, "매출(원)", 3001000)
    assert run(question, "매출(백만원)", 13)


@pytest.mark.parametrize("header", ["매출(USD)", "매출(EUR)", "매출(%)", "매출", "매출(USD/KRW)"])
def test_currency_cannot_be_ignored_or_invented_from_a_raw_number(header):
    assert not run("부서별 매출 합계가 100원 초과인 그룹", header, 100)


@pytest.mark.parametrize("unit", ["달러", "유로", "엔", "파운드", "¥"])
def test_a_consumed_currency_word_is_never_treated_as_unitless(unit):
    assert not run(f"부서별 매출 합계가 100{unit} 초과인 그룹", "매출(KRW)", 100)


@pytest.mark.parametrize("header,threshold", [("매출(천원)", .1), ("매출(원)", 100), ("매출(억원)", .000001)])
def test_supported_header_scales_are_common_source_metadata(header, threshold):
    assert run("부서별 매출 합계가 100원 초과인 그룹", header, threshold)


def test_raw_threshold_without_currency_or_magnitude_keeps_stored_units():
    assert run("부서별 매출 합계가 100 초과인 그룹", "매출(백만원)", 100)


def test_english_magnitude_is_not_discarded_after_prefix_comparison():
    assert run("sum 매출 by 부서 having sum 매출 > $100 million", "매출(USD million)", 100)
    assert not run("sum 매출 by 부서 having sum 매출 > $100 million", "매출(USD)", 100)
    assert run("sum 매출 by 부서 having sum 매출 > $100 million", "매출(USD)", 100000000)


def test_ambiguous_number_format_or_report_scale_fails_closed():
    question = "부서별 매출 합계가 1억원 초과인 그룹"
    assert not run(question, "매출(백만원)", 100, number_format='0,,"원"')
    assert not run(question, "매출(원)", 100000000, context=(("A1", "단위: 백만원"),))


@pytest.mark.parametrize("value", ["Total", "Average"])
def test_quoted_aggregate_word_filters_are_never_masked(value):
    question = f"상태가 '{value}'인 부서별 매출 합계가 100 초과인 그룹"
    condition = TabularFilter(column_id="C", operator="equals", value=value)
    assert run(question, "매출", 100, filters=[condition])
    assert not run(question, "매출", 100)


def test_quoted_source_header_is_not_a_second_requested_statistic():
    assert run("부서별 'Average' 합계가 100 초과인 그룹", "Average", 100)
    assert not run("부서별 'Average' 평균과 합계가 100 초과인 그룹", "Average", 100)


def test_source_filter_cannot_be_erased_by_later_having_marker():
    question = "상태가 'Total'인 부서별 매출 평균과 합계가 100 초과인 그룹"
    condition = TabularFilter(column_id="C", operator="equals", value="Total")
    assert not run(question, "매출", 100, filters=[condition])


def test_common_won_annotation_does_not_strip_an_unrelated_source_qualifier():
    from app.agent.query.ambiguity_labels import label_base

    assert label_base("매출(억원)") == "매출"
    assert label_base("매출(조건)") == "매출(조건)"
