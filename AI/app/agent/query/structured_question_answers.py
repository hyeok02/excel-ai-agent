"""Route multi-part and Boolean requests before single-question shortcuts."""
from app.agent.query.boolean_filter_language import boolean_question
from app.agent.query.boolean_source_answers import boolean_source_answer
from app.agent.query.composite_execution import composite_answer
from app.agent.query.composite_split import split_compound_question


async def structured_question_answer(service, question, sources, *, intent_override=None,
                                     allow_composite=True, intents=None):
    if allow_composite and split_compound_question(question, sources) is not None:
        intent = intent_override or await service._question_intent(question, sources.summary)
        return await composite_answer(question, sources, intent, service._answer_prepared)
    if not boolean_question(question):
        return None
    # No single-query shortcut may silently discard an OR/NOT branch.
    answer = boolean_source_answer(question, sources.summary, sources.index, intent_override)
    if answer.status != "insufficient_evidence" or intent_override is not None:
        return answer
    intent = await service._question_intent(question, sources.summary)
    if intents is not None:
        intents.append(intent)
    return boolean_source_answer(question, sources.summary, sources.index, intent)
