"""Exact-source deterministic aggregates never discard unexplained conditions."""
import pytest

from app.agent.query.source_aggregate_answers import source_aggregate_answer
from tests.tabular_query_fixtures import table_fixture


def fixture(second=False, reverse=False):
    rows = [["West", 7, 10, 32], ["East", 7, 30, 24], ["West", 3, 50, 35]]
    if reverse:
        rows.reverse()
    blocks = [(2, 2, [["Region", "Class", "Reading", "Temperature"], *rows])]
    if second:
        blocks.append((15, 2, [["Region", "Class", "Reading", "Temperature"], *rows]))
    return table_fixture(blocks, sheet_name="Measurements")


@pytest.mark.parametrize("question,expected", [
    ("전체 Reading 합계는 얼마야?", "90"),
    ("Reading 평균은 얼마야?", "30"),
    ("Reading 최솟값은 얼마야?", "10"),
    ("Reading 최댓값은 얼마야?", "50"),
    ("Region이 West인 Reading 합계를 알려줘", "60"),
    ("Class가 7인 데이터의 Reading 평균은 얼마야?", "20"),
    ("Measurements에서 Temperature가 30보다 큰 데이터의 Reading 평균은 얼마야?", "30"),
    ("Region별 Reading 합계를 비교해줘", "West"),
    ("What is the sum of Reading?", "90"),
    ("sum of Reading where Temperature > 30", "60"),
])
@pytest.mark.parametrize("reverse", [False, True])
def test_exact_header_aggregates_are_source_validated(question, expected, reverse):
    summary, index = fixture(reverse=reverse)
    answer = source_aggregate_answer(question, summary, index)
    assert answer is not None
    assert expected in answer.answer
    assert answer.verification.level == "request_checked"


@pytest.mark.parametrize("question", [
    "Reading 평균을 2024년만 알려줘",
    "Reading 합계를 서울만 알려줘",
    "Region이 West인 Reading 합계에서 5 빼줘",
    "Class가 7인 데이터의 Reading 평균을 미래에 예측해줘",
    "Reading의 평균과 표준편차 알려줘",
    "Reading 평균은 얼마야? Profit은?",
    "Reading 평균을 달러로 환산해줘",
    "Region이 West 또는 East인 Reading 합계",
    "Temperature가 30보다 크지 않은 Reading 합계",
    "Temperature가 30 이상 40 이하인 Reading 합계",
    "다른Reading 합계 알려줘",
])
def test_unknown_scope_or_unsupported_operation_never_gets_dropped(question):
    summary, index = fixture()
    assert source_aggregate_answer(question, summary, index) is None


def test_matching_tables_remain_ambiguous():
    summary, index = fixture(second=True)
    assert source_aggregate_answer("Reading 합계는 얼마야?", summary, index) is None


def test_large_source_aggregate_uses_complete_source_scan(monkeypatch):
    from tests.support.large_workbook_fixtures import parsed, workbook
    from app.agent.query import index as index_module
    from app.services.workbook_details import analysis_samples
    monkeypatch.setattr(index_module, "MAX_INDEXED_CELLS", 16)
    monkeypatch.setattr(analysis_samples, "MAX_ANALYSIS_REGION_CELLS", 12)
    monkeypatch.setattr(analysis_samples, "MAX_ANALYSIS_SHEET_CELLS", 12)
    summary, index, _ = parsed(workbook({"Readings": [["Category", "Reading"],
        *[["West", value] for value in range(1, 41)]]}))
    answer = source_aggregate_answer("Readings의 Reading 평균은 얼마야?", summary, index)
    assert answer is not None and "20.5" in answer.answer
    assert answer.verification.level == "request_checked"
    assert "full_source_scan" in answer.verification.checks
