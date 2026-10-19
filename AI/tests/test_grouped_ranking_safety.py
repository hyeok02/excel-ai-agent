"""Unseen tail errors and interrupted scans cannot yield a green ranking."""
import pytest

from app.agent.query.workbook_source_models import SourceReadLimits
from tests.support.grouped_ranking_fixtures import grouped_plan, raw_plan, records, source
from tests.support.large_workbook_fixtures import (
    ask, assert_not_certified, assert_stream_checked, equal, offline, parsed, tiny_caps, workbook,
)


@pytest.mark.parametrize("grouped", [False, True])
@pytest.mark.parametrize("field", [1, 2])
def test_uncached_tail_sort_or_group_formula_is_not_blank(tiny_caps, grouped, field):
    matrix = records()
    if not grouped and field == 2:
        field = 1
    matrix[-1][field] = "=MISSING_EXTERNAL_VALUE()"
    summary, index, _ = source(matrix)
    plan = grouped_plan(summary, order_by="B", limit=2) if grouped else raw_plan(summary)
    question = ("Records 시트 Department별 Amount 합계 상위 2개 보여줘" if grouped else
                "Records 시트 Amount 상위 2개 Record와 Amount 보여줘")
    answer = ask(question, summary, index, plan)
    assert_not_certified(answer)


def test_uncached_sort_key_not_returned_as_a_display_column_still_blocks_ranking(tiny_caps):
    matrix = records()
    matrix[-1][1] = "=MISSING_EXTERNAL_VALUE()"
    summary, index, _ = source(matrix)
    answer = ask("Records 시트 Amount 상위 2개 Record 보여줘", summary, index,
                 raw_plan(summary, columns=("A",)))
    assert_not_certified(answer)


@pytest.mark.parametrize("grouped", [False, True])
@pytest.mark.parametrize("last_format", ['"EUR" #,##0', "0.0%"])
def test_late_mixed_unit_cannot_be_compared_even_between_separate_groups(tiny_caps, grouped, last_format):
    book = workbook({"Records": records()})
    for row in book.active.iter_rows(min_row=2, min_col=2, max_col=2):
        row[0].number_format = '"USD" #,##0'
    book.active["B11"].number_format = last_format
    summary, index, _ = parsed(book)
    plan = grouped_plan(summary, order_by="B", limit=2) if grouped else raw_plan(summary)
    question = ("Records 시트 Department별 Amount 합계 상위 2개 보여줘" if grouped else
                "Records 시트 Amount 상위 2개 Record와 Amount 보여줘")
    assert_not_certified(ask(question, summary, index, plan))


def test_equal_numeric_totals_in_different_currency_groups_cannot_be_ranked(tiny_caps):
    matrix = [["Record", "Amount", "Department"], ["A", 100, "Alpha"],
              ["B", 0, "Alpha"], ["C", 100, "Beta"]]
    book = workbook({"Records": matrix})
    book.active["B2"].number_format = book.active["B3"].number_format = '"USD" #,##0'
    book.active["B4"].number_format = '"EUR" #,##0'
    summary, index, _ = parsed(book)
    answer = ask("Records 시트 Department별 Amount 합계 상위 1개 보여줘", summary, index,
                 grouped_plan(summary, order_by="B", limit=1))
    assert_not_certified(answer)


@pytest.mark.parametrize("grouped", [False, True])
@pytest.mark.parametrize("bad", [True, "99999", "not available"])
def test_non_numeric_late_sort_measure_is_not_silently_omitted(tiny_caps, grouped, bad):
    matrix = records()
    matrix[-1][1] = bad
    summary, index, _ = source(matrix)
    plan = grouped_plan(summary, order_by="B", limit=2) if grouped else raw_plan(summary)
    question = ("Records 시트 Department별 Amount 합계 상위 2개 보여줘" if grouped else
                "Records 시트 Amount 상위 2개 Record와 Amount 보여줘")
    assert_not_certified(ask(question, summary, index, plan))


@pytest.mark.parametrize("grouped", [False, True])
def test_cumulative_budget_exhaustion_discards_partial_rank_or_groups(tiny_caps, grouped):
    summary, index, _ = source(limits=SourceReadLimits(max_cells=45))
    with index.source_provider.scan_rows("Records", "A1:D3") as scan:
        assert len(list(scan)) == 3
    assert scan.complete
    plan = grouped_plan(summary, order_by="B", limit=2) if grouped else raw_plan(summary)
    question = ("Records 시트 Department별 Amount 합계 상위 2개 보여줘" if grouped else
                "Records 시트 Amount 상위 2개 Record와 Amount 보여줘")
    answer = ask(question, summary, index, plan)
    assert_not_certified(answer)
    assert "full_source_scan" not in answer.verification.checks


@pytest.mark.parametrize("question", [
    "Records 시트 Amount 상위 2개 Record와 Amount 동점 모두 포함해서 보여줘",
    "Records 시트 Amount top 2 Record and Amount including all ties",
])
def test_all_ties_request_cannot_be_silently_truncated_to_exact_n(tiny_caps, question):
    summary, index, _ = source()
    assert_not_certified(ask(question, summary, index, raw_plan(summary)))


@pytest.mark.parametrize("grouped", [False, True])
def test_known_filter_excludes_an_unknown_measure_before_ranking(tiny_caps, grouped):
    matrix = records()
    matrix[-1][1], matrix[-1][3] = "=MISSING_EXTERNAL_VALUE()", "inactive"
    summary, index, _ = source(matrix)
    filters = [equal("D", "active")]
    plan = (grouped_plan(summary, order_by="B", limit=1, filters=filters) if grouped else
            raw_plan(summary, limit=2, filters=filters))
    question = ("Records 시트 State가 active인 Department별 Amount 합계 상위 1개 보여줘" if grouped else
                "Records 시트 State가 active인 Amount 상위 2개 Record와 Amount 보여줘")
    answer = ask(question, summary, index, plan)
    assert_stream_checked(answer)
    assert ("Alpha" if grouped else "Third") in answer.answer
    assert "Tail" not in answer.answer


def test_group_count_does_not_require_an_unused_measure_formula_result(tiny_caps):
    matrix = records()
    matrix[-1][1] = "=MISSING_EXTERNAL_VALUE()"
    summary, index, _ = source(matrix)
    answer = ask("Records 시트 Department별 행 개수 알려줘", summary, index,
                 grouped_plan(summary, operation="row_count", columns=()))
    assert_stream_checked(answer)
    assert "Delta" in answer.answer
