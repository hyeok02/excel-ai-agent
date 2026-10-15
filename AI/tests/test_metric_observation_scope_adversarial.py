from app.agent.query.metric_observation_answers import metric_observation_answer
from app.agent.query.metric_scalar_answers import metric_scalar_answer
from tests.test_metric_observation_adversarial import _checked, _index, _report
import pytest


def test_filtered_population_cannot_be_ignored_by_period_scalar_shortcut():
    index = _index({"Report": _report("All markets", [2024, 2025], [100, 110])})
    answer = metric_observation_answer("2025년 매출 중 국내 매출만 알려줘", None, index)
    assert not _checked(answer)


def test_requested_currency_conversion_is_not_silently_certified_in_source_currency():
    index = _index({"Report": _report("Alpha Company", [2024, 2025], [100, 110])})
    answer = metric_observation_answer("2025년 매출을 원화로 환산해서 알려줘", None, index)
    assert not _checked(answer)


def test_distinct_entity_blocks_on_one_sheet_cannot_borrow_latest_period():
    index = _index({"Report": _report("Alpha Company", [2024, 2025], [100, 110]) + [[], []]
                    + _report("Beta Company", [2025, 2026], [200, 220])})
    answer = metric_observation_answer("Alpha Company의 최신 매출은?", None, index)
    assert not _checked(answer) or ("110" in answer.answer and "220" not in answer.answer)


def test_no_unit_caption_from_unrelated_parallel_table():
    index = _index({"Report": [
        ["Currency", None, None, "Currency"],
        ["USD", None, None, "EUR"],
        ["Revenue", 110, None, "Cost", 55],
    ]}, number_format="General")
    answer = metric_scalar_answer("Revenue는 얼마야?", None, index)
    assert not _checked(answer) or ("미국 달러" in answer.answer and "유로" not in answer.answer)


def test_same_numeric_value_with_distinct_currency_cannot_collapse_to_one_observation():
    index = _index({"USD ledger": [["Amounts in USD millions"], [None, "Annual actual"],
                                    ["Period", "2024-12-31", "2025-12-31"], ["Revenue", 100, 110]],
                    "EUR ledger": [["Amounts in EUR millions"], [None, "Annual actual"],
                                    ["Period", "2024-12-31", "2025-12-31"], ["Revenue", 100, 110]]},
                   number_format="General")
    answer = metric_observation_answer("2025년 매출은?", None, index)
    assert not _checked(answer)


def test_same_end_date_annual_and_quarter_are_not_interchangeable():
    index = _index({"Report": [
        [None, "Annual actual", "Quarter actual"],
        ["Period", "2025-12-31", "2025-12-31"],
        ["Revenue", 110, 30],
    ]})
    annual = metric_observation_answer("2025년 연간 Revenue는 얼마야?", None, index)
    quarter = metric_observation_answer("2025년 12월 31일 종료 분기 Revenue는 얼마야?", None, index)
    assert annual is not None and "110" in annual.answer and "30" not in annual.answer
    assert quarter is not None and "30" in quarter.answer and "110" not in quarter.answer


@pytest.mark.parametrize("question", [
    "2025년 매출총이익은 얼마야?",
    "2025년 직원 1인당 매출은 얼마야?",
    "2025년 순부채는 얼마야?",
])
def test_metric_alias_substring_does_not_replace_a_different_requested_measure(question):
    index = _index({"Report": _report("Alpha Company", [2024, 2025], [100, 110], [12, 14])})
    answer = metric_observation_answer(question, None, index)
    assert not _checked(answer)
