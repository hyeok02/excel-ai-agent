"""Classifier boundary; ordinary failures retain the deterministic fallback."""
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.quota_errors import raise_for_quota_exhaustion


async def resolve_question_intent(classifier, question, summary):
    if classifier is None:
        return QuestionIntent.from_keywords(question)
    try:
        return await classifier.classify(question, summary)
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        return QuestionIntent.from_keywords(question)
