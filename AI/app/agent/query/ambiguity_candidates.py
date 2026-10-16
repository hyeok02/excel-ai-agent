"""Small source-addressed clarification candidates shared by detectors."""
from dataclasses import dataclass

from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus
from app.agent.query.clarification_options import source_clarification_options


@dataclass(frozen=True)
class AmbiguousCandidate:
    label: str
    scope: str
    details: str
    followup: str
    cells: tuple = ()


def clarification_answer(question, candidates, summary=None, data_index=None):
    shown = list(dict.fromkeys(candidates))[:6]
    lines = ["질문에 맞는 원본 항목이 여러 개여서 하나를 임의로 선택하지 않았습니다.",
             "다음 후보 중 원하는 범위를 지정해 주세요."]
    for number, candidate in enumerate(shown, 1):
        lines.append(f"{number}. {candidate.scope} · {candidate.label} · {candidate.details}")
        lines.append(f"   다시 질문: {candidate.followup}")
    if len(candidates) > len(shown):
        lines.append(f"후보 {len(candidates)}개 중 {len(shown)}개를 표시했습니다. 시트나 표 범위를 지정해 주세요.")
    cells = list(dict.fromkeys(cell for candidate in shown for cell in candidate.cells))
    return QuestionAnswer(
        question=question, answer="\n".join(lines),
        status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE, confidence=0,
        selected_tools=["clarify_source_scope"], evidence=[_evidence(cell) for cell in cells[:18]],
        limitations=["원본 후보를 찾았지만 질문의 대상·기간·단위가 하나로 확정되지 않았습니다."],
        clarification_options=source_clarification_options(question, shown, summary, data_index),
    )
