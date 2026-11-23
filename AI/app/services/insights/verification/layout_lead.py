"""The first sentence a file is introduced with ('이 파일은 …', '이 파일에는 … (출처: …)'), kept as it was
when a layout narrative writes the rest of the overview."""
import re

LEAD = re.compile(r"^\s*(이 파일(?:은|에는)\s.+?다\.(?:\s*\([^)]*\))?)", re.S)


def keep_lead(final, canonical, report, context, index):
    from app.services.insights.verification.file_lead import described
    if not getattr(canonical, "_layout", False):
        return described(final, context, force=getattr(canonical, "_sheets", False))
    from app.services.insights.narratives.source_narratives import source_narrative_report
    from app.services.insights.verification.prepared_validation import PreparedValidation
    from app.services.insights.verification.validator import validate_workbook_insights
    before = source_narrative_report(context, layout=False)
    original = validate_workbook_insights(report, context, PreparedValidation(context, index, before))
    found = LEAD.match(original.overview or "")
    if found:
        final.overview = f"{' '.join(found[1].split())} {final.overview}".strip()
    return described(final, context, force=getattr(canonical, "_sheets", False))
