"""A proven cell lookup is not proof of an interpretation or a causal claim."""
import re

from app.agent.query.models import QuestionAnswerStatus, QuestionAnswerVerification

INTERPRETATION = re.compile(
    r"뜻|의미|왜|원인|때문|이유|안정적|정상인가|정상인거|정상이라는|"
    r"\b(?:why|means|meaning|cause|causes|caused|because|imply|implies|stable)\b|"
    r"\bwhat\b.{0,80}\bmean\b", re.I,
)


def asks_interpretation(question: str) -> bool:
    return bool(INTERPRETATION.search(question))


def finish_interpretation_answer(answer):
    if answer.status == "insufficient_evidence" or not asks_interpretation(
        answer.resolved_question or answer.question
    ):
        return answer
    checks = answer.verification.checks
    if "header_positions" in checks:
        return answer  # The structural-relation response already carries this boundary.
    note = "원본의 값·설명은 확인했지만, 질문에서 묻는 의미·원인까지 입증한 것은 아닙니다."
    level = "source_checked" if answer.verification.level == "request_checked" else answer.verification.level
    return answer.model_copy(update={
        "status": QuestionAnswerStatus.LIMITED, "confidence": min(answer.confidence, 0.7),
        "limitations": list(dict.fromkeys([*answer.limitations, note])),
        "verification": QuestionAnswerVerification(
            level=level,
            checks=[check for check in checks if check != "request_alignment"] + ["interpretation_unverified"],
        ),
    })
