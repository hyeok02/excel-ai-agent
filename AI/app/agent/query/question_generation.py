"""Generate from an execution snapshot without changing its source context."""
import asyncio

from app.agent.query.answer_validation import validate_answer
from app.agent.query.context import execution_context
from app.agent.query.gpt_calc_answers import keep_draft
from app.agent.query.grounded_interpretation import interpreted_answer
from app.agent.query.question_validation import unclear_draft_answer
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.series_value_answers import series_value_answer
from app.agent.query.source_value_answers import source_value_answer
from app.agent.query.workbook_summary_answers import _verified_summary_source


async def generate_answer(generator, question, summary, execution, truncated, index=None):
    draft = await generator.generate(question, summary.filename, execution_context(execution))
    keep_draft(draft, execution)  # shown, marked unverified, if nothing else answers in the end
    answer = unclear_draft_answer(question, draft) or validate_answer(question, draft, execution, truncated)
    if answer.status != "insufficient_evidence":
        # A reading the question asks for is shown with its cited figures, when its numbers hold.
        return interpreted_answer(question, draft, execution, truncated) or answer if draft.interpretive else answer
    # Only an unanswered draft is replaced: by a value every matching source agrees on, else by
    # the draft's own reading where each of its numbers is a cell or verified fact it cites.
    settled = source_value_answer(question, summary, index) if index is not None else None
    if settled is None and index is not None:  # a stored period value outranks the draft's reading of it
        settled = await asyncio.to_thread(series_value_answer, question, summary, index)
    if settled is None and unclear_draft_answer(question, draft) is None:
        settled = interpreted_answer(question, draft, execution, truncated, index)
    return settled or answer


async def read_whole_file(generator, question, summary, execution, truncated, intent, overview):
    """A whole-file question asking for more than a summary ("어떤 제품에 집중해야 할까?") has the
    overview's verified facts read for it; the overview stays the answer when no reading holds."""
    source = _verified_summary_source(execution)
    if not (generator and intent.whole_workbook and intent.kind not in {"summary", "brief", "structure"}
            and source and overview.answer in source[0]):
        return overview
    try:
        draft = await generator.generate(question, summary.filename, execution_context(execution))
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        return overview
    return (interpreted_answer(question, draft, execution, truncated) if draft.interpretive else None) or overview
