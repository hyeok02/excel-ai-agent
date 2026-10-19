"""Output bounds must disclose truncation and preserve selected rank order."""
import pytest

from app.agent.query.index import build_workbook_data_index
from tests.support.grouped_ranking_fixtures import grouped_plan, line_with, raw_plan, source
from tests.support.large_workbook_fixtures import ask, assert_stream_checked, offline, tiny_caps


def many_rows():
    return [["Record", "Amount", "Department"],
            *[[f"Item{number:03}", number, "Only"] for number in range(1, 141)]]


def test_streaming_top_one_hundred_displays_every_requested_rank(tiny_caps):
    summary, index, _ = source(many_rows())
    answer = ask("Records 시트 Amount 상위 100개 Record와 Amount 보여줘", summary, index,
                 raw_plan(summary, limit=100))
    assert_stream_checked(answer)
    rows = [line for line in answer.answer.splitlines() if line.startswith("Record:")]
    assert len(rows) == 100
    assert "Item140" in rows[0] and "Item041" in rows[-1]
    assert "Item040" not in answer.answer


def test_sort_without_explicit_limit_discloses_the_fifty_row_display_limit(tiny_caps):
    summary, index, _ = source(many_rows())
    answer = ask("Records 시트 Amount 내림차순으로 Record와 Amount 보여줘", summary, index,
                 raw_plan(summary, limit=None))
    assert answer.status == "limited", answer.model_dump()
    assert answer.verification.level == "request_checked"
    rows = [line for line in answer.answer.splitlines() if line.startswith("Record:")]
    assert len(rows) == 50
    assert "Item140" in rows[0] and "Item091" in rows[-1]
    assert "Item090" not in answer.answer
    assert any("140" in limitation and "50" in limitation for limitation in answer.limitations)


@pytest.mark.parametrize("provider", [False, True])
def test_fully_indexed_grouped_query_works_without_streaming_or_provider(provider):
    summary, index, content = source()
    if not provider:
        index = build_workbook_data_index(summary.filename, content, {"Records"})
    assert not index.truncated
    answer = ask("Records 시트 Department별 Amount 합계 상위 2개 보여줘", summary, index,
                 grouped_plan(summary, order_by="B", limit=2))
    assert answer.status == "answered", answer.model_dump()
    assert answer.verification.level == "request_checked"
    assert "full_source_scan" not in answer.verification.checks
    assert "합계 970" in line_with(answer, "Delta")
    assert "합계 24" in line_with(answer, "Beta")


def test_group_cutoff_tie_is_disclosed_and_does_not_expand_exact_n(tiny_caps):
    summary, index, _ = source()
    answer = ask("Records 시트 Department별 행 개수 상위 1개 보여줘", summary, index,
                 grouped_plan(summary, operation="row_count", columns=(), limit=1))
    assert answer.status == "limited", answer.model_dump()
    assert answer.verification.level == "request_checked"
    assert "Alpha" in answer.answer and "Beta" not in answer.answer
    assert any("동점" in limitation for limitation in answer.limitations)
