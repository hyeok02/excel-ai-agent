"""Bind an explicit sheet selection without dropping the previous request's terms."""
from app.agent.query.conversation_language import selected_scope_sheet, scope_only_followup
from app.agent.query.conversation_models import ContextResolutionDraft
from app.agent.query.references import extract_references


def bound_scope_question(question, context, entries, index) -> ContextResolutionDraft | None:
    sheet = selected_scope_sheet(question, index)
    if sheet is None or not context.turns:
        return None
    latest_id = f"turn:{len(context.turns) - 1}"
    if not any(entry["id"] == latest_id for entry in entries):
        return None
    # This is the user's earlier request, not an answer or a claimed fact. The
    # resulting request still runs through the complete original-cell verifier.
    previous = context.turns[-1].question
    if scope_only_followup(previous, index):
        return None
    other_sheets = {row.sheet_name for row in index.rows} - {sheet}
    if any(name.casefold() in previous.casefold() for name in other_sheets):
        return None
    if any(ref.rsplit("!", 1)[0].strip("'").casefold() != sheet.casefold()
           for ref in extract_references(previous)):
        return None
    resolved = f"{sheet} 시트에서 {previous}"
    if len(resolved) > 1000:
        return None
    return ContextResolutionDraft(status="resolved", question=resolved, context_ids=[latest_id])
