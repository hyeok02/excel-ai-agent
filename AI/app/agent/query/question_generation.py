"""Generate from an execution snapshot without changing its source context."""
from app.agent.query.answer_validation import validate_answer
from app.agent.query.context import execution_context
from app.agent.query.question_validation import unclear_draft_answer
from app.agent.query.source_value_answers import source_value_answer


async def generate_answer(generator, question, summary, execution, truncated, index=None):
    draft = await generator.generate(question, summary.filename, execution_context(execution))
    answer = unclear_draft_answer(question, draft) or validate_answer(question, draft, execution, truncated)
    # Only an unanswered draft is replaced, by a value every matching source agrees on.
    if index is not None and answer.status == "insufficient_evidence":
        return source_value_answer(question, summary, index) or answer
    return answer
