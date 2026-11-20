"""One year's series compared ("2024년 발전량이 가장 많은 에너지원"), totals left out."""
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.references import normalize_reference
from app.agent.query.series_topic_names import named_topic, series_words
from app.agent.query.series_value_answers import MAX_TOPICS
from app.services.insights.display.source_labels import source_label, source_unit
from app.services.insights.facts.context import build_workbook_context
from app.services.insights.facts.series_scalars import displayed_text, displayed_value, unit
from app.services.insights.narratives.all_series_facts import all_series_facts
from app.services.insights.narratives.narrative_values import finite, reference
from app.services.insights.narratives.table_schema import column
from app.services.insights.narratives.vertical_latest_format import _suffix
from app.services.insights.narratives.vertical_latest_items import metric_name
from app.services.insights.narratives.vertical_latest_narratives import _basis_priority
from app.services.insights.narratives.vertical_latest_series import _series


def cross_series_answer(question, summary, index, year, high, resolver):
    found = named_topic(series_words(question), _topics(build_workbook_context(summary)), resolver)
    if found is not None and found[1] is not None and "total" not in found[1].casefold():
        return None  # one series is named: its own year, not a comparison across series
    best = None
    for sheet in build_workbook_context(summary).get("sheets", []):
        for header, section, section_cell, records, unit_note in (_series(sheet) if isinstance(sheet, dict) else ()):
            rows = [record for record in records if record[0].year == year]
            if _basis_priority(section) in (1, 3) or len({record[0].year for record in records}) != len(records) or len(rows) != 1:
                continue
            values = [(cell, rows[0][2].get(column(cell), {})) for cell in header[1:] if "total" not in metric_name(cell).casefold()]
            values = [(cell, value) for cell, value in values if finite(value.get("value"))]
            if len(values) >= 2 and (best is None or len(values) > len(best[4])):
                best = (sheet.get("name", ""), section, section_cell, rows[0][1], values, unit_note)
    if best is None:
        return None
    sheet, section, section_cell, period, values, unit_note = best
    cell, value = (max if high else min)(values, key=lambda item: item[1]["value"])
    if sum(1 for _, other in values if other["value"] == value["value"]) != 1:
        return None
    units = unit(value) or (source_unit(unit_note["value"]) if unit_note else "")
    references = [reference(sheet, item["cell"]) for item in (section_cell, period, cell, value, *(other for _, other in values)) if item]
    cells = {normalize_reference(item.reference): item for row in index.rows for item in row.cells}
    cited = [cells.get(normalize_reference(item)) for item in references]
    if None in cited:
        return None
    scope = " · ".join(part for part in (sheet, section) if part)
    text = (f"{scope}의 {year}년 값 중 가장 {'높은' if high else '낮은'} 항목은 {source_label(metric_name(cell))} "
            f"{displayed_text(value, displayed_value(value))}{_suffix(units)}입니다 (합계 열을 뺀 {len(values)}개 항목 비교).")
    return QuestionAnswer(question=question, status=QuestionAnswerStatus.LIMITED, confidence=0.8, selected_tools=["verified_series"],
                          answer=text, evidence=[_evidence(item) for item in dict.fromkeys(cited)], limitations=[],
                          verification=QuestionAnswerVerification(level="source_checked", checks=["source_values", "ranking"]))


def _topics(context):
    return list(dict.fromkeys(str(item.topic) for _, item in all_series_facts(context) if item.topic))[:MAX_TOPICS]
