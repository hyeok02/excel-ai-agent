"""Whole-table populations survive source limits without changing workbook policy."""
import pytest

from app.agent.query import index as index_module
from app.agent.query.tabular_catalog import build_query_tables
from tests.support.large_workbook_fixtures import (
    ask, assert_stream_checked, equal, offline, parsed, plan_for,
    tiny_caps, workbook,
)


def rows():
    return [["Record", "Amount", "Group"], *[[f"Item{n}", n, "ordinary"] for n in range(1, 9)]]


def test_later_authorized_sheet_remains_queryable_after_global_index_exhaustion(tiny_caps, monkeypatch):
    monkeypatch.setattr(index_module, "MAX_INDEXED_CELLS", 6)
    book = workbook({"Earlier": rows(), "Records": rows()})
    summary, index, _ = parsed(book)
    assert not any(row.sheet_name == "Records" for row in index.rows)
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_stream_checked(answer)
    assert "합계 36" in answer.answer


@pytest.mark.parametrize("operation,expected", [("row_count", "1건"), ("numeric_summary", "합계 888")])
def test_filter_match_only_after_sample_limit_is_included(tiny_caps, operation, expected):
    matrix = rows() + [["Tail", 888, "special"]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    plan = plan_for(summary, operation=operation, columns=() if operation == "row_count" else ("B",),
                    filters=[equal("C", "special")])
    suffix = "행 개수" if operation == "row_count" else "Amount 합계"
    answer = ask(f"Records 시트 Group이 special인 {suffix}는?", summary, index, plan)
    assert_stream_checked(answer)
    assert expected in answer.answer


def test_hidden_tail_row_is_excluded_and_disclosed(tiny_caps):
    book = workbook({"Records": rows()})
    book.active.row_dimensions[9].hidden = True
    summary, index, _ = parsed(book)
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert answer.status in {"answered", "limited"}
    assert "합계 28" in answer.answer and "숨겨진 1개 행" in answer.answer
    assert "full_source_scan" in answer.verification.checks


def test_explicit_hidden_measure_column_keeps_existing_qna_policy(tiny_caps):
    book = workbook({"Records": rows()})
    book.active.column_dimensions["B"].hidden = True
    summary, index, _ = parsed(book)
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_stream_checked(answer)
    assert "합계 36" in answer.answer


def test_native_totals_and_values_below_table_are_not_double_counted(tiny_caps):
    matrix = rows() + [["TOTAL", 36, "summary"]]
    book = workbook({"Records": matrix})
    book.active.tables["SourceTable1"].totalsRowCount = 1
    book.active["B12"] = 90000
    summary, index, _ = parsed(book)
    tables = [table for table in build_query_tables(summary) if table.reference == "A1:C9"]
    assert len(tables) == 1
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_stream_checked(answer)
    assert "합계 36" in answer.answer and "90,000" not in answer.answer


def test_blank_record_gaps_do_not_end_the_source_scan(tiny_caps):
    matrix = rows() + [[None, None, None], ["Tail", 400, "ordinary"]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_stream_checked(answer)
    assert "합계 436" in answer.answer and "숫자 9건" in answer.answer


def test_category_count_includes_tail_and_blank_observations(tiny_caps):
    matrix = rows() + [["Tail", 400, "special"], ["Empty", 500, None]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    plan = plan_for(summary, operation="frequencies", columns=("C",))
    answer = ask("Records 시트 Group 값별 건수는?", summary, index, plan)
    assert_stream_checked(answer)
    assert "‘ordinary’ 8건" in answer.answer and "‘special’ 1건" in answer.answer
    assert "빈칸 1건" in answer.answer and "총 10건" in answer.answer


def test_blank_measure_does_not_erase_the_nonempty_record(tiny_caps):
    matrix = rows() + [["Tail", None, "ordinary"]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_stream_checked(answer)
    assert "합계 36" in answer.answer and "숫자 8건, 빈칸 1건" in answer.answer


def test_unneeded_formula_does_not_block_a_fully_known_measure(tiny_caps):
    matrix = rows() + [["Tail", 400, "=MISSING_EXTERNAL_VALUE()"]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_stream_checked(answer)
    assert "합계 436" in answer.answer


def test_plain_range_without_an_excel_table_keeps_its_original_bottom(tiny_caps):
    book = workbook({"Records": rows()})
    book.active.tables.clear()
    summary, index, _ = parsed(book)
    assert not summary.sheets[0].tables
    assert build_query_tables(summary)[0].reference.endswith("C9")
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_stream_checked(answer)
    assert "합계 36" in answer.answer


def test_known_filter_excludes_a_tail_formula_without_guessing_its_value(tiny_caps):
    matrix = rows() + [["Tail", "=MISSING_EXTERNAL_VALUE()", "outside"]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    plan = plan_for(summary, filters=[equal("C", "ordinary")])
    answer = ask("Records 시트 Group이 ordinary인 Amount 합계는?", summary, index, plan)
    assert_stream_checked(answer)
    assert "합계 36" in answer.answer


def test_explicit_hidden_filter_column_is_reread_from_original(tiny_caps):
    book = workbook({"Records": rows() + [["Tail", 888, "special"]]})
    book.active.column_dimensions["C"].hidden = True
    summary, index, _ = parsed(book)
    plan = plan_for(summary, filters=[equal("C", "special")])
    answer = ask("Records 시트 Group이 special인 Amount 합계는?", summary, index, plan)
    assert_stream_checked(answer)
    assert "합계 888" in answer.answer
