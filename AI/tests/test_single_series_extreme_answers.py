"""Offline regression coverage for one-series annual extreme questions."""
from app.agent.query.single_series_extreme_answers import single_series_extreme_answer
from app.agent.query.time_series_answers import time_series_answer
from tests.support.single_series_extreme_fixtures import asthma_source


def test_exact_metric_answers_largest_annual_increase_from_all_source_values():
    summary, index = asthma_source()
    answer = time_series_answer(
        "Asthma Attack Prevalence가 가장 많이 증가한 년도는 언제야?", summary, index,
    )
    assert answer.status == "answered", answer.model_dump()
    assert answer.verification.level == "request_checked", answer.model_dump()
    assert "2022" in answer.answer and "2021" in answer.answer
    assert "12.0%" in answer.answer and "20.0%" in answer.answer and "8.0%p" in answer.answer
    assert answer.selected_tools == ["chronological_interval_extreme"]


def test_interval_wording_and_temporal_continuation_answer_same_source_calculation():
    summary, index = asthma_source()
    answer = time_series_answer(
        "Asthma Attack Prevalence가 가장 많이 증가한 구간은 어디야? 년 단위로", summary, index,
    )
    assert answer.status == "answered", answer.model_dump()
    assert "2021" in answer.answer and "2022" in answer.answer and "8.0%p" in answer.answer


def test_generic_korean_prevalence_requests_source_metric_choice_instead_of_guessing():
    summary, index = asthma_source()
    answer = time_series_answer("천식 유병률이 가장 많이 증가한 년도는 언제야?", summary, index)
    assert answer.status == "insufficient_evidence", answer.model_dump()
    assert len(answer.clarification_options) == 2, answer.model_dump()
    labels = {option.label for option in answer.clarification_options}
    assert labels == {"Asthma Attack Prevalence", "Current Asthma Prevalence"}


def test_source_choice_reenters_the_same_verified_calculator():
    summary, index = asthma_source()
    ambiguous = time_series_answer("천식 유병률이 가장 많이 증가한 년도는 언제야?", summary, index)
    option = next(
        item for item in ambiguous.clarification_options
        if item.label == "Current Asthma Prevalence"
    )
    chosen = time_series_answer(option.question, summary, index)
    assert chosen.status == "answered", chosen.model_dump()
    assert chosen.verification.level == "request_checked", chosen.model_dump()
    assert "2022" in chosen.answer and "2021" in chosen.answer and "3.0%p" in chosen.answer


def test_leading_missing_period_is_trimmed_but_internal_gap_is_not_silently_skipped():
    summary, index = asthma_source()
    leading = time_series_answer(
        "Current Asthma Prevalence가 가장 많이 증가한 년도는 언제야?", summary, index,
    )
    assert leading.status == "answered", leading.model_dump()
    assert "2022" in leading.answer and "3.0%p" in leading.answer

    gap_summary, gap_index = asthma_source(internal_gap=True)
    gap = time_series_answer(
        "Asthma Attack Prevalence가 가장 많이 증가한 년도는 언제야?",
        gap_summary,
        gap_index,
    )
    assert gap.status != "answered", gap.model_dump()
    assert gap.verification.level != "request_checked", gap.model_dump()


def test_group_ranking_question_is_not_claimed_by_single_series_handler():
    summary, index = asthma_source()
    assert single_series_extreme_answer(
        "전체 기간 중 인원이 가장 많이 증가한 부서는 어디야?", summary, index,
    ) is None
