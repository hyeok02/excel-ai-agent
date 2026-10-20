"""Categorical part/whole trends over a fully verified original population."""
from app.agent.query.derived_trend_answers import unavailable
from app.agent.query.derived_trend_request import DerivedRequest
from app.agent.query.derived_trend_render import render_derived
from app.agent.query.grouped_share_trend_sources import category_share_source
from app.agent.query.grouped_share_trend_calculations import category_share_points
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification


def grouped_share_trend_answer(question, summary, index):
    try:
        bound = category_share_source(question, summary, index)
        if bound is None:
            return None
        source, target, named = bound
        points, series, references, group_count = category_share_points(source, target, named, index)
        label = f"{target.value} {source.metric.header}"
        total_label = f"전체 {source.metric.header}({source.headers[target.column_id].value}별 합계)"
        request = DerivedRequest("share", (label, total_label), component=True)
        text, _ = render_derived(request, points, (), series, source.note)
        text += (f"\n분모는 같은 원본 표의 {group_count}개 범주를 매 시점 모두 합산한 값입니다. "
                 "각 범주·날짜의 값이 하나씩 존재하며 범주 집합과 단위가 같은지 확인했습니다.")
        return QuestionAnswer(
            question=question, answer=text, status="answered", confidence=1,
            selected_tools=["chronological_trend", "derived_trend", "grouped_share_trend"],
            evidence=[_evidence(cell) for cell in references], limitations=[],
            verification=QuestionAnswerVerification(level="request_checked", checks=[
                "table_scope", "metric", "complete_series", "source_values", "chronological_order", "calculation",
                "turning_points", "aligned_periods", "positive_denominator", "operand_lineage", "unit",
                "request_alignment", "aligned_entity_scope", "complete_category_grid", "no_subtotal_double_count",
            ]),
        )
    except (ValueError, TypeError, ArithmeticError) as error:
        return unavailable(question, str(error) or "전체 범주 비중을 원본과 대조하지 못했습니다.")
