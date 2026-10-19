"""Trends use full authorized source reads, not a truncated search prefix."""
from dataclasses import replace
from datetime import datetime, timedelta

from app.agent.query.trend_sources import trend_candidates
from app.agent.query.workbook_source_models import SourceReadLimits
from tests.support.large_workbook_fixtures import offline, parsed, tiny_caps, workbook


def _book(last=10):
    matrix = [["Date", "Total Employees"]]
    matrix.extend([[datetime(2025, 1, 1) + timedelta(days=n), 100 + n] for n in range(12)])
    matrix[-1][1] = last
    return workbook({"History": matrix})


def test_truncated_index_rereads_the_late_period(tiny_caps):
    summary, index, _ = parsed(_book())
    assert index.truncated
    candidates = trend_candidates(summary, index, "전체 직원 수의 기간별 추이를 설명해줘")
    valid = [candidate for candidate in candidates if not candidate.error]
    assert len(valid) == 1
    assert len(valid[0].observations) == 12
    assert valid[0].observations[-1].value.value == 10
    assert valid[0].observations[-1].value.address == "B13"


def test_uncached_tail_formula_cannot_disappear_after_index_prefix(tiny_caps):
    summary, index, _ = parsed(_book("=EXTERNAL()"))
    candidates = trend_candidates(summary, index, "전체 직원 수의 기간별 추이를 설명해줘")
    assert candidates and all(candidate.error for candidate in candidates)
    assert candidates[0].error == "missing_or_invalid_value"


def test_read_budget_never_certifies_a_prefix(tiny_caps):
    summary, index, _ = parsed(_book(), limits=SourceReadLimits(max_cells=8))
    candidates = trend_candidates(summary, index, "전체 직원 수의 기간별 추이를 설명해줘")
    assert candidates and all(candidate.error for candidate in candidates)


def test_wrong_workbook_source_digest_disables_reread(tiny_caps):
    summary, index, _ = parsed(_book())
    index = replace(index, source_digest="not-this-workbook")
    candidates = trend_candidates(summary, index, "전체 직원 수의 기간별 추이를 설명해줘")
    assert candidates and all(candidate.error for candidate in candidates)


def test_hidden_rows_beyond_index_are_counted_and_excluded(tiny_caps):
    book = _book()
    book.active.row_dimensions[13].hidden = True
    summary, index, _ = parsed(book)
    candidates = trend_candidates(summary, index, "전체 직원 수의 기간별 추이를 설명해줘")
    valid = [candidate for candidate in candidates if not candidate.error]
    assert len(valid) == 1 and valid[0].hidden_rows == 1
    assert len(valid[0].observations) == 11
    assert valid[0].observations[-1].value.address == "B12"
