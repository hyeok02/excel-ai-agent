"""Mark a trend-stage refusal that only failed to bind its series.

Such a refusal says nothing about the data, so later stages (planning and the
checked draft) may still answer; it remains the fallback when they cannot.
Refusals that state a data fact (missing values, duplicate periods, a period
outside the source) keep their explanation and are never marked.
"""
from app.agent.query.models import QuestionAnswerStatus, QuestionAnswerVerification

UNBOUND = "series_unbound"


def unbound(answer):
    return answer.model_copy(update={"verification": QuestionAnswerVerification(checks=[UNBOUND])})


def refused_without_basis(answer):
    return bool(answer is not None and answer.status == QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
                and not answer.evidence and not answer.clarification_options)


def is_unbound(answer):
    return refused_without_basis(answer) and UNBOUND in answer.verification.checks


def answers_nothing(answer):
    """A refusal citing cells it could not use, or a reading that says the asked thing is unknown: not an answer."""
    return bool(answer is not None and not answer.clarification_options and (
        "question_unanswered" in answer.verification.checks
        or answer.status == QuestionAnswerStatus.INSUFFICIENT_EVIDENCE and answer.evidence))
