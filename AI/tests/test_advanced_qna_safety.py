"""Missing source values and read exhaustion must never publish partial totals."""
import pytest

from app.agent.query.workbook_source_models import SourceReadLimits
from tests.support.advanced_qna_fixtures import (
    condition, distinct_plan, group_plan, partition_plan, records, source,
)
from tests.support.large_workbook_fixtures import ask, assert_not_certified, offline, parsed, tiny_caps, workbook


def feature_plan(summary, feature):
    if feature == "having":
        return ("Records 시트 Department별 Amount 합계가 70 초과인 그룹 보여줘",
                group_plan(summary, having=[condition(70)]))
    if feature == "share":
        return ("Records 시트 Department별 Amount 합계의 전체 비중 알려줘",
                group_plan(summary, share_of_total=True))
    if feature == "distinct":
        return "Records 시트 Customer 중복 제외 개수 알려줘", distinct_plan(summary)
    return ("Records 시트 각 Department별 Amount 상위 2개 Record와 Amount 보여줘",
            partition_plan(summary))


@pytest.mark.parametrize("feature", ["having", "share", "distinct", "partition"])
def test_mid_scan_budget_exhaustion_discards_every_partial_advanced_result(tiny_caps, feature):
    summary, index, _ = source(limits=SourceReadLimits(max_cells=50))
    with index.source_provider.scan_rows("Records", "A1:E3") as scan:
        assert len(list(scan)) == 3
    assert scan.complete
    question, plan = feature_plan(summary, feature)
    answer = ask(question, summary, index, plan)
    assert_not_certified(answer)
    assert "full_source_scan" not in answer.verification.checks


@pytest.mark.parametrize("feature", ["having", "share", "partition"])
@pytest.mark.parametrize("field", [1, 2])
def test_uncached_tail_measure_or_group_formula_is_never_ignored(tiny_caps, feature, field):
    matrix = records()
    matrix[-1][field] = "=MISSING_EXTERNAL_VALUE()"
    summary, index, _ = source(matrix)
    question, plan = feature_plan(summary, feature)
    assert_not_certified(ask(question, summary, index, plan))


@pytest.mark.parametrize("values", [(0, 0), (10, -10), (10, -1)])
def test_share_with_zero_total_or_negative_component_is_not_a_fake_percentage(tiny_caps, values):
    matrix = [["Record", "Amount", "Department"], ["A", values[0], "Alpha"],
              ["B", values[1], "Beta"]]
    summary, index, _ = source(matrix)
    question, plan = feature_plan(summary, "share")
    assert_not_certified(ask(question, summary, index, plan))


@pytest.mark.parametrize("feature", ["having", "share", "partition"])
def test_mixed_currency_in_late_measure_is_not_compared_or_combined(tiny_caps, feature):
    book = workbook({"Records": records()})
    for row in book.active.iter_rows(min_row=2, min_col=2, max_col=2):
        row[0].number_format = '"USD" #,##0'
    book.active["B9"].number_format = '"EUR" #,##0'
    summary, index, _ = parsed(book)
    question, plan = feature_plan(summary, feature)
    assert_not_certified(ask(question, summary, index, plan))


def test_partition_bound_never_discards_tail_groups_silently(tiny_caps):
    matrix = [["Record", "Amount", "Department"]]
    matrix.extend([f"Item{number}", number, f"Group{number}"] for number in range(1, 1_003))
    summary, index, _ = source(matrix)
    question, plan = feature_plan(summary, "partition")
    answer = ask(question, summary, index, plan)
    assert_not_certified(answer)


@pytest.mark.parametrize("header,value", [("Amount (백만원)", 120), ("Amount (천원)", 120_000)])
def test_scaled_header_having_cannot_compare_physical_threshold_as_raw_value(header, value):
    summary, index, _ = source([["Record", header, "Department"], ["First", value, "Alpha"],
                                ["Second", value / 2, "Beta"]])
    answer = ask("Records 시트 Department별 Amount 합계가 1억원 초과인 그룹 보여줘", summary, index,
                 group_plan(summary, having=[condition(100_000_000)]))
    # 120 million KRW is above 100 million KRW; certifying zero groups is wrong.
    assert_not_certified(answer)


@pytest.mark.parametrize("unit", ["USD", "EUR", "%"])
def test_currency_threshold_cannot_be_applied_to_an_incompatible_source_unit(unit):
    summary, index, _ = source([["Record", f"Amount ({unit})", "Department"],
                                ["First", 120, "Alpha"], ["Second", 80, "Beta"]])
    answer = ask("Records 시트 Department별 Amount 합계가 100원 초과인 그룹 보여줘", summary, index,
                 group_plan(summary, having=[condition(100)]))
    assert_not_certified(answer)


@pytest.mark.parametrize("currency", ["달러", "유로", "엔", "파운드"])
def test_korean_currency_words_cannot_be_consumed_then_ignored(currency):
    summary, index, _ = source([["Record", "Amount (KRW)", "Department"],
                                ["First", 120, "Alpha"], ["Second", 80, "Beta"]])
    answer = ask(f"Records 시트 Department별 Amount 합계가 100{currency} 초과인 그룹 보여줘", summary, index,
                 group_plan(summary, having=[condition(100)]))
    assert_not_certified(answer)


def test_compound_korean_quantity_cannot_certify_wrong_numeric_threshold():
    summary, index, _ = source([["Record", "Amount (KRW)", "Department"],
                                ["First", 4_000_000, "Alpha"], ["Second", 2_000_000, "Beta"]])
    answer = ask("Records 시트 Department별 Amount 합계가 1천3백만원 초과인 그룹 보여줘", summary, index,
                 group_plan(summary, having=[condition(3_001_000)]))
    # 1천3백만 = 13,000,000, not independent 1천 + 3백만 = 3,001,000.
    assert_not_certified(answer)
