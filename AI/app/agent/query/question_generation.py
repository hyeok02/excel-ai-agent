"""Generate from an execution snapshot without changing its source context."""
from app.agent.query.answer_validation import validate_answer
from app.agent.query.context import execution_context
from app.agent.query.question_validation import unclear_draft_answer


async def generate_answer(generator, question, summary, execution, truncated):
    draft = await generator.generate(question, summary.filename, execution_context(execution))
    if clarification := unclear_draft_answer(question, draft):
        return clarification
    return validate_answer(question, draft, execution, truncated)
