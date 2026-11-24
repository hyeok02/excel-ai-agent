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
    lead = " ".join(found[1].split()) if found else ""
    if lead and not _same_sheets(lead, final):  # '가격표' introduced over facts read from '시트통합데이터'
        from app.services.insights.verification.file_lead import _lead
        lead = _lead(final, context)
    if lead:
        final.overview = f"{lead} {final.overview}".strip()
    return described(final, context, force=getattr(canonical, "_sheets", False))


def _same_sheets(lead, report):
    """Whether the sheets a lead names (‘가격표’ 시트) are among those the report's facts are read from."""
    from app.services.insights.verification.validation_index import extract_references
    named = {" ".join(name.split()).casefold() for name in re.findall(r"‘([^’]+)’(?:[·‘’\w\s]*?)\s*시트", lead)}
    cited = {" ".join(ref.split("!", 1)[0].strip("'").split()).casefold() for item in report.insights
             for evidence in item.evidence for ref in extract_references(evidence)}
    return not named or not cited or bool(named & cited)
