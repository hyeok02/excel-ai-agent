"""One period's value of a series the plan route could not bind ("2025년 총발전량은?").

Table_1_01 holds annual totals and monthly blocks in one region, so no query table covers it,
while the insight report reads it section by section. The question's word is read among every
series name, as for a trend; of the series' sections, annual totals come first and the asked
year (or year and month) must be exactly one row there. The answer is that source cell, with
the reading and the section stated. Partial bases (year to date, rolling) never stand in.
"""
import re

from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.references import normalize_reference
from app.agent.query.series_topic_names import named_topic, series_words
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

MAX_TOPICS = 250
_YEAR = re.compile(r"(?<!\d)((?:19|20|21)\d{2})\s*년")
_MONTH = re.compile(r"(?<!\d)(1[0-2]|[1-9])\s*월")
# A change, ranking, share or aggregate is another question, not one stored value.
_OTHER = re.compile(r"추이|변화|증가|감소|가장|최대|최소|최고|최저|평균|합계|총합|비교|비율|비중|순위|대비|차이|부터|까지|~")


def series_value_answer(question, summary, index, resolver=None):
    years, months = set(_YEAR.findall(question)), set(_MONTH.findall(question))
    if summary is None or index is None or len(years) != 1 or len(months) > 1 or _OTHER.search(question):
        return None
    year, month = int(next(iter(years))), int(next(iter(months))) if months else None
    context = build_workbook_context(summary)
    topics = list(dict.fromkeys(str(item.topic) for _, item in all_series_facts(context) if item.topic))[:MAX_TOPICS]
    if (found := named_topic(series_words(question), topics, resolver)) is None:
        return None
    word, topic, _ = found
    hits = []
    for sheet in context.get("sheets", []):
        for header, section, section_cell, records, unit_note in (_series(sheet) if isinstance(sheet, dict) else ()):
            annual = len({record[0].year for record in records}) == len(records)
            priority = _basis_priority(section)
            if priority in (1, 3) or annual == (month is not None):
                continue  # a partial basis, or a monthly block for a yearly question (and back)
            rows = [record for record in records if record[0].year == year and (month is None or record[0].month == month)]
            for cell in header[1:]:
                value = rows[0][2].get(column(cell), {}) if len(rows) == 1 else {}
                if metric_name(cell) == topic and finite(value.get("value")):
                    hits.append((priority, sheet.get("name", ""), section, section_cell, cell, rows[0][1], value, unit_note))
    if not hits:
        return None
    best = [hit for hit in hits if hit[0] == min(hit[0] for hit in hits)]
    if len({hit[6].get("value") for hit in best}) != 1:
        return None  # two tables state different values for the same period
    _, sheet, section, section_cell, header, period, value, unit_note = best[0]
    units = unit(value) or (source_unit(unit_note["value"]) if unit_note else "")
    references = [reference(sheet, item["cell"]) for item in (header, header.get("_parent"), period, value,
                                                               section_cell, unit_note if not unit(value) else None) if item]
    cells = {normalize_reference(cell.reference): cell for row in index.rows for cell in row.cells}
    cited = [cells.get(normalize_reference(item)) for item in references]
    if None in cited:
        return None
    when = f"{year}년" + (f" {month}월" if month else "")
    scope = " · ".join(part for part in (sheet, section) if part)
    shown = displayed_text(value, displayed_value(value)) + _suffix(units)
    return QuestionAnswer(
        question=question, status=QuestionAnswerStatus.LIMITED, confidence=0.8, selected_tools=["verified_series"],
        answer=f"해석: ‘{word}’ → {topic}\n{scope}의 {source_label(topic)} {when} 값은 {shown}입니다.",
        evidence=[_evidence(cell) for cell in dict.fromkeys(cited)],
        limitations=[f"질문의 표현을 원본 계열로 옮긴 해석(‘{word}’ → {topic})이 의도와 맞는지 확인해 주세요."],
        verification=QuestionAnswerVerification(level="source_checked",
                                                checks=["source_values", "period", "semantic_alias_resolved"]))
