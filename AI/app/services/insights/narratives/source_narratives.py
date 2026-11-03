"""Deterministic semantic facts; model prose may reuse them, not invent bindings."""
import re

from app.services.insights.narratives.categorical_narratives import categorical_report
from app.services.insights.narratives.comparable_narratives import comparable_transaction_report
from app.services.insights.narratives.flag_narratives import flag_matrix_report
from app.services.insights.narratives.horizontal_trends import horizontal_trend_report
from app.services.insights.models import WorkbookInsightReport
from app.services.insights.narratives.ranked_narratives import ranked_report
from app.services.insights.facts.sheet_scope import comparison_sheet
from app.services.insights.narratives.snapshot_narratives import snapshot_report
from app.services.insights.narratives.numeric_table_narratives import numeric_table_report
from app.services.insights.narratives.table_narratives import table_report
from app.services.insights.narratives.trend_narratives import trend_report
from app.services.insights.narratives.record_summary import record_summary_report
from app.services.insights.narratives.vertical_latest_narratives import vertical_latest_report
from app.services.insights.verification.validation_index import extract_references
from app.services.insights.display.source_labels import source_caption
from app.services.insights.narratives.source_context import compact_facts, source_table_context
from app.services.insights.narratives.source_qualifications import source_qualifications


def source_narrative_report(context):
    options = []
    reporters = (
        comparable_transaction_report, record_summary_report, vertical_latest_report,
        trend_report, ranked_report, horizontal_trend_report,
        table_report, flag_matrix_report,
        categorical_report, snapshot_report, numeric_table_report,
    )
    for mode_order, reporter in enumerate(reporters):
        items, overview = reporter(context)
        if items:
            comparison, source_order = _source_scope(context, items)
            options.append((comparison, source_order, mode_order, items, overview))
    if not options:
        return WorkbookInsightReport(overview="", insights=[], limitations=[])
    preferred = [option for option in options if option[2] == 0]
    primary = [option for option in options if not option[0]]
    _, _, mode, items, overview = min(preferred or primary or options,
                                   key=lambda option: (option[2], option[1]))
    has_context = reporters[mode] is record_summary_report
    if not has_context:
        captions = []
        qualifications = []
        for item in items:
            caption, refs = source_table_context(context, item)
            captions.append(caption)
            if caption:
                item.evidence = list(dict.fromkeys([*item.evidence, *refs]))
            qualification, refs = source_qualifications(context, item)
            if qualification:
                item.fact += " " + qualification
                item.evidence = list(dict.fromkeys([*item.evidence, *refs]))
            qualifications.append(qualification)
        if reporters[mode] in (horizontal_trend_report, vertical_latest_report):
            overview = compact_facts(items)
        # Status notes qualify the exact years shown, not every value in a file.
        notes = []
        for qualification in qualifications:
            for sentence in re.split(r"(?<=\.)\s+(?=(?:\d{4}년 수치는|원본 주석:))", qualification):
                sentence = sentence.strip().rstrip(".")
                if sentence and sentence not in notes:
                    notes.append(sentence)
        if notes:
            overview += " " + ". ".join(notes) + "."
        if captions and captions[0]:
            overview = f"이 파일에는 {source_caption(captions[0])} 자료가 담겨 있습니다. {overview}"
            has_context = True
    report = WorkbookInsightReport(overview=overview, insights=items, limitations=[])
    report._overview_has_context = has_context
    return report


def _source_scope(context, items):
    sheets = {
        str(sheet.get("name", "")).casefold(): (index, comparison_sheet(sheet))
        for index, sheet in enumerate(context.get("sheets", []))
        if isinstance(sheet, dict)
    }
    sources = []
    for item in items:
        for evidence in item.evidence:
            for ref in extract_references(str(evidence)):
                if ref.split("!", 1)[0] in sheets:
                    sources.append(sheets[ref.split("!", 1)[0]])
    return (all(source[1] for source in sources),
            min((source[0] for source in sources), default=len(sheets)))
