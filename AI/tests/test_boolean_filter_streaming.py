"""The indexed and full-source engines must select the same boolean population."""
import pytest

from app.agent.query.boolean_source_answers import boolean_source_answer
from app.agent.query.tabular_execution import execute_tabular_query
from tests.support.large_workbook_fixtures import offline, parsed, tiny_caps, workbook
from tests.test_boolean_filter_queries import query_plan


def data():
    return [["Item", "Region", "Status", "Amount"],
            *[[f"ID{n}", "North" if n % 3 else "South", "Closed" if n % 2 else "Open", n]
              for n in range(1, 17)]]


@pytest.mark.parametrize("grouped", [False, True])
def test_full_scan_includes_or_matches_beyond_sample(tiny_caps, grouped):
    summary, index, _ = parsed(workbook({"Records": data()}))
    suffix = "Region별 Amount 합계" if grouped else "Amount 합계"
    question = "(Region = 'North' OR Region = 'South') AND NOT Status = 'Closed' " + suffix
    result = boolean_source_answer(question, summary, index)
    assert result.status == "answered" and result.verification.level == "request_checked", result
    assert "full_source_scan" in result.verification.checks
    if grouped:
        assert "합계 18" in result.answer and "합계 54" in result.answer
    else:
        assert "합계 72" in result.answer


def test_indexed_grouped_reducer_uses_boolean_not_flat_and():
    summary, index, _ = parsed(workbook({"Records": data()}))
    question = "(Region = 'North' OR Region = 'South') AND NOT Status = 'Closed' Region별 Amount 합계"
    answer = execute_tabular_query(query_plan(question, summary, group_by=["B"]), summary, index, question)
    assert answer.status == "answered", answer
    assert "합계 18" in answer.answer and "합계 54" in answer.answer


def test_or_condition_still_rejects_cross_currency_sum(tiny_caps):
    matrix = [["Item", "Region", "Amount", "Currency"],
              *[[f"ID{n}", "North" if n < 16 else "South", n, "USD" if n < 16 else "EUR"]
                for n in range(1, 17)]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    answer = boolean_source_answer("Region = 'North' OR Region = 'South' Amount 합계", summary, index)
    assert answer.status == "insufficient_evidence" and answer.verification.level == "unverified"
    assert "통화" in answer.answer


def test_explicit_currency_filter_keeps_valid_or_population(tiny_caps):
    matrix = [["Item", "Region", "Amount", "Currency"],
              *[[f"ID{n}", "North" if n % 3 else "South", n, "USD" if n < 16 else "EUR"]
                for n in range(1, 17)]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    question = "(Region = 'North' OR Region = 'South') AND Currency = 'USD' Amount 합계"
    answer = boolean_source_answer(question, summary, index)
    assert answer.status == "answered" and "합계 120" in answer.answer


def test_invalid_numeric_value_in_tail_is_not_treated_as_false(tiny_caps):
    matrix = data()
    matrix[-1][-1] = "not a number"
    summary, index, _ = parsed(workbook({"Records": matrix}))
    answer = boolean_source_answer("Amount >= 10 OR Status = 'Closed' 행 수", summary, index)
    assert answer.status == "insufficient_evidence" and answer.verification.level == "unverified"
