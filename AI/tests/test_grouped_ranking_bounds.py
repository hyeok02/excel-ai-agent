"""Bounded grouping must fail closed rather than discard tail categories."""
import pytest

from tests.support.grouped_ranking_fixtures import grouped_plan, line_with, source
from tests.support.large_workbook_fixtures import (
    ask, assert_not_certified, assert_stream_checked, fresh_index, offline, parsed, tiny_caps, workbook,
)


def test_group_state_limit_cannot_publish_a_prefix_group_winner(tiny_caps, monkeypatch):
    from app.agent.query import grouped_tabular_state
    monkeypatch.setattr(grouped_tabular_state, "MAX_GROUPS", 2)
    summary, index, _ = source()
    answer = ask("Records 시트 Department별 Amount 합계 상위 1개 보여줘", summary, index,
                 grouped_plan(summary, order_by="B", limit=1))
    assert_not_certified(answer)
    assert "full_source_scan" not in answer.verification.checks


def test_real_group_state_limit_never_silently_ignores_tail_categories(tiny_caps):
    matrix = [["Record", "Amount", "Department"]]
    matrix.extend([f"Item{n}", n, f"Group{n}"] for n in range(1, 1_003))
    summary, index, _ = source(matrix)
    answer = ask("Records 시트 Department별 Amount 합계 상위 1개 보여줘", summary, index,
                 grouped_plan(summary, order_by="B", limit=1))
    assert_not_certified(answer)


@pytest.fixture(scope="module")
def one_large_group():
    matrix = [["Record", "Amount", "Department"]]
    matrix.extend([f"Item{n}", 1, "Only"] for n in range(1, 10_002))
    matrix.append(["Last", -1, "Only"])
    return parsed(workbook({"Records": matrix}))


def test_single_group_size_is_not_confused_with_group_state_limit(one_large_group):
    summary, _, content = one_large_group
    index = fresh_index(summary, content)
    assert index.truncated_for({"Records"})
    answer = ask("Records 시트 Department별 Amount 합계 알려줘", summary, index, grouped_plan(summary))
    assert_stream_checked(answer)
    assert "합계 10,000" in line_with(answer, "Only")
    assert "숫자 10002건" in line_with(answer, "Only")


def test_hidden_row_does_not_contribute_to_group_winner(tiny_caps):
    from tests.support.grouped_ranking_fixtures import records
    book = workbook({"Records": records()})
    book.active.row_dimensions[10].hidden = True
    summary, index, _ = parsed(book)
    answer = ask("Records 시트 Department별 Amount 합계 상위 1개 보여줘", summary, index,
                 grouped_plan(summary, order_by="B", limit=1))
    assert answer.status in {"answered", "limited"}, answer.model_dump()
    assert "합계 70" in line_with(answer, "Delta")
    assert "숨겨진 1개 행" in answer.answer
    assert "full_source_scan" in answer.verification.checks


def test_native_totals_row_cannot_become_a_ranked_group(tiny_caps):
    from tests.support.grouped_ranking_fixtures import records
    matrix = records() + [["TOTAL", 987, "Summary", "all"]]
    book = workbook({"Records": matrix})
    book.active.tables["SourceTable1"].totalsRowCount = 1
    summary, index, _ = parsed(book)
    answer = ask("Records 시트 Department별 Amount 합계 상위 1개 보여줘", summary, index,
                 grouped_plan(summary, order_by="B", limit=1))
    assert_stream_checked(answer)
    assert "합계 970" in line_with(answer, "Delta")
    assert "Summary" not in answer.answer
