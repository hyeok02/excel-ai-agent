from dataclasses import replace

from app.agent.query.ambiguity_answers import ambiguous_source_answer
from app.agent.query.ambiguity_tables import table_candidates
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.metric_observation_answers import metric_observation_answer
from app.agent.query.tabular_catalog import build_query_tables
from tests.tabular_query_fixtures import table_fixture


def test_grouped_comparison_is_not_replaced_by_a_single_table_choice():
    summary, index = table_fixture([
        (1, 1, [["Department", "Headcount"], ["Research", 10], ["Service", 20]]),
        (8, 4, [["Department", "Headcount"], ["Research", 20], ["Service", 30]]),
    ])
    question = "부서 등 항목별 전체 직원 수 변화를 시작 값과 마지막 값 기준으로 비교해줘"
    assert table_candidates(question, summary, index)
    assert ambiguous_source_answer(question, summary, index, QuestionIntent(False, "comparison")) is None
    assert ambiguous_source_answer(question, summary, index) is None


def test_independently_verified_latest_record_wins_over_duplicate_header_choices():
    summary, index = table_fixture([
        (1, 1, [["Company", "Headcount", "Headcount As Of"],
                ["Aurora Company", 100, "2030-06-01"], ["Aurora Company", 120, "2030-07-01"]]),
        (8, 5, [["Company", "Headcount", "Other metric"], ["Aurora Company", 90, 7]]),
    ])
    question = "Aurora Company의 최신 Headcount와 기준일은?"
    intent = QuestionIntent(False, "cell_lookup")
    assert table_candidates(question, summary, index)
    observed = metric_observation_answer(question, summary, index, intent)
    assert observed is not None and observed.verification.level == "request_checked"
    assert ambiguous_source_answer(question, summary, index, intent) is None


def test_top_caption_is_not_a_request_for_rank_column(monkeypatch):
    summary, index = table_fixture([
        (3, 1, [["RANK", "PERCENT HELD (%)"], [1, 10], [2, 0.5]]),
        (10, 5, [["RANK", "PERCENT HELD (%)"], [1, 5], [2, 0.2]]),
    ])
    tables = [replace(table, context=((f"{table.sheet_name}!A1", "TOP 40 CONTRIBUTORS"),))
              for table in build_query_tables(summary)]
    monkeypatch.setattr("app.agent.query.ambiguity_tables.build_query_tables", lambda _: tables)
    candidates = table_candidates("TOP 40 CONTRIBUTORS에서 지분율이 1% 이상인 건수", summary, index)
    assert len(candidates) == 2
    assert all(candidate.label == "PERCENT HELD (%)" for candidate in candidates)
    explicit = table_candidates("TOP 40 CONTRIBUTORS의 RANK 합계", summary, index)
    assert len(explicit) == 2
    assert all(candidate.label == "RANK" for candidate in explicit)
