"""Answer temporal extrema rankings only after whole-population validation."""
from app.agent.query.change_ranking_calculations import calculate_ranking
from app.agent.query.change_ranking_render import render_ranking
from app.agent.query.change_ranking_request import parse_change_ranking_request
from app.agent.query.change_ranking_sources import ranking_sources
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification


def ranked_change_answer(question, summary, index):
    request = parse_change_ranking_request(question)
    if request is None:
        return None
    sources = ranking_sources(question, summary, index, request)
    if sources.error:
        return _unavailable(question, sources.error)
    if not sources.series:
        if not getattr(index, "rows", ()):
            return None
        return _unavailable(question, "질문에 맞는 전체 비교 대상과 기간별 원본 값을 연결하지 못했습니다.")
    try:
        ranking = calculate_ranking(sources.series, request)
        net = calculate_ranking(sources.series, request, "net") if request.basis == "auto" else None
        text = render_ranking(ranking, request, sources.group_label, net)
    except (ValueError, TypeError, ArithmeticError) as error:
        return _unavailable(question, str(error) or "비교 계산의 날짜·값·단위를 확정하지 못했습니다.")
    limitations = list(sources.limitations)
    if not all(unit.known for _, units in sources.series for unit in units):
        limitations.append("수치는 원본 저장값 기준입니다. 통화·수량 단위까지는 확정하지 못했습니다.")
    references = []
    for candidate, units in sources.series:
        references.extend(candidate.context)
        for point, unit in zip(candidate.observations, units):
            references.extend((point.label, point.period_cell, point.value, *point.context_cells,
                               *point.entity_cells, *point.unit_context, *unit.references))
    return QuestionAnswer(
        question=question, answer=text, status="limited" if limitations else "answered",
        confidence=0.9 if limitations else 1, selected_tools=["chronological_change_ranking"],
        evidence=[_evidence(cell) for cell in dict.fromkeys(references)], limitations=limitations,
        verification=QuestionAnswerVerification(
            level="source_checked" if limitations else "request_checked",
            checks=["table_scope", "metric", "complete_population", "complete_series", "source_values",
                    "chronological_order", "comparison_basis", "calculation", "ranking", "all_ties"]
                   + (["unit", "request_alignment"] if not limitations else []),
        ),
    )


def _unavailable(question, reason):
    return QuestionAnswer(question=question, answer=reason, status="insufficient_evidence", confidence=0,
                          selected_tools=["chronological_change_ranking"], evidence=[], limitations=[reason])
