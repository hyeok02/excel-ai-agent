"""Compare multiple explicit complete metrics without weakening source checks."""
from app.agent.query.ambiguity_metric_scope import bind_explicit_metric_scope
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification
from app.agent.query.trend_comparison_dates import checked_comparison_periods
from app.agent.query.trend_comparison_render import comparison_sections
from app.agent.query.trend_comparison_scope import (
    MAX_COMPARISON_SERIES, comparison_candidates, comparison_limits, comparison_missing_metrics, explicit_series,
)
from app.agent.query.trend_request import trend_request_error


def comparison_answer(question, prepared_valid, rows, named, summary, index, *, scope_ambiguous=False):
    """Input candidates have already passed original-source/date-range checks."""
    series = explicit_series(question, prepared_valid)
    if not series:
        return None
    if len(series) > MAX_COMPARISON_SERIES:
        return _unavailable(question, "한 번에 비교할 항목을 6개 이하로 지정해 주세요. 일부 항목만 임의로 골라 답하지 않았습니다.")
    observations = tuple(point for candidate, _ in series for point in candidate.observations)
    _, scoped_question = bind_explicit_metric_scope(question, observations)
    if scoped_question != question:
        import re
        scoped_question = re.sub(r"범위(?:에서|의|내)?|\brange\b", " ", scoped_question, flags=re.I)
    series, error = checked_comparison_periods(scoped_question, series, named)
    if error:
        return _unavailable(question, error)
    if error := trend_request_error(scoped_question, observations, named):
        return _unavailable(question, error)
    limitations = comparison_limits(series)
    if scope_ambiguous:
        limitations.append("다른 원본 후보에는 날짜 축이 여러 개 있습니다. 명시한 표의 항목별 추이만 표시하며 대상 표와 직접 비교 결과를 확정하지 않았습니다.")
    try:
        text, evidence = comparison_sections(series, not limitations)
    except (ValueError, TypeError, ArithmeticError):
        return _unavailable(question, "각 항목의 전체 날짜·단위·계산 결과를 확정하지 못해 비교 결과를 표시하지 않았습니다.")
    if limitations:
        text = "직접 수치 비교에는 확인하지 못한 조건이 있어, 항목별 원본 추이를 구분해 표시합니다.\n\n" + text
    return QuestionAnswer(
        question=question, answer=text, status="limited" if limitations else "answered",
        confidence=0.8 if limitations else 1, selected_tools=["chronological_trend", "compare_trend_series"],
        evidence=evidence, limitations=list(dict.fromkeys(limitations)),
        verification=QuestionAnswerVerification(
            level="source_checked" if limitations else "request_checked",
            checks=["table_scope", "metric", "complete_series", "source_values",
                    "chronological_order", "calculation", "turning_points", "all_requested_metrics"]
                   + (["alternative_source_ambiguous"] if scope_ambiguous else ["request_alignment"])
                   + ([] if limitations else ["aligned_periods", "aligned_units", "aligned_entity_scope"]),
        ),
    )


def _unavailable(question, reason):
    return QuestionAnswer(question=question, answer=reason, status="insufficient_evidence", confidence=0,
                          selected_tools=["chronological_trend", "compare_trend_series"],
                          evidence=[], limitations=[reason])
