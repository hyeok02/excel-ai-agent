"""The average of one year's stored monthly values ("2024년 평균 병상 점유율은?"), as a last resort.

A series laid out month by month holds no yearly value; the question asks the arithmetic mean of
that year's months. The series is read as for a single period's value: its name among every series
name, from monthly sections only, and the asked year must have at least two months. When the
question names a sheet (a scoped follow-up of a clarification), only that sheet is read; series
on several sheets with different months stay unanswered. Every month used is cited and counted.
"""
import re
from statistics import fmean

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
from app.services.insights.narratives.vertical_latest_series import _series

MAX_TOPICS, MAX_EVIDENCE = 250, 40
_YEAR = re.compile(r"(?<!\d)((?:19|20|21)\d{2})\s*년")
_AVERAGE = re.compile(r"평균")
_OTHER = re.compile(r"추이|변화|증가|감소|가장|최대|최소|최고|최저|합계|총합|비교|비율|비중|순위|대비|차이|부터|까지|~|(?<!\d)(?:1[0-2]|[1-9])\s*월")


def period_average_answer(question, summary, index, resolver=None):
    years = set(_YEAR.findall(question))
    if summary is None or index is None or len(years) != 1 or not _AVERAGE.search(question) or _OTHER.search(question):
        return None
    year, context = int(next(iter(years))), build_workbook_context(summary)
    sheets = [sheet for sheet in context.get("sheets", []) if isinstance(sheet, dict)]
    named = [sheet for sheet in sheets if str(sheet.get("name", "")).casefold() in question.casefold()]
    topics = list(dict.fromkeys(str(item.topic) for _, item in all_series_facts(context) if item.topic))[:MAX_TOPICS]
    if (found := named_topic(series_words(question), topics, resolver)) is None:
        return None
    word, topic, _ = found
    hits = []
    for sheet in named or sheets:
        for header, section, _, records, unit_note in _series(sheet):
            if len({record[0].year for record in records}) == len(records):
                continue  # a yearly series already holds the year's value; that is another question
            months = [record for record in records if record[0].year == year]
            for cell in header[1:]:
                values = [record[2].get(column(cell), {}) for record in months]
                if metric_name(cell) == topic and len(values) >= 2 and all(finite(item.get("value")) for item in values):
                    hits.append((sheet.get("name", ""), section, cell, months, values, unit_note))
    if len(hits) != 1:
        return None  # nothing, or the series on several sheets: which one is not this question's to decide
    sheet, section, header, months, values, unit_note = hits[0]
    if len({unit(item) for item in values}) != 1:
        return None
    mean = fmean(float(item["value"]) for item in values)
    shown = displayed_text({**values[0], "value": mean}, displayed_value({**values[0], "value": mean}))
    units = unit(values[0]) or (source_unit(unit_note["value"]) if unit_note else "")
    references = [reference(sheet, header["cell"]), *(reference(sheet, item["cell"])
                  for record, value in zip(months, values) for item in (record[1], value))]
    cells = {normalize_reference(cell.reference): cell for row in index.rows for cell in row.cells}
    cited = [cells.get(normalize_reference(item)) for item in references]
    if None in cited:
        return None
    scope = " · ".join(part for part in (sheet, section) if part)
    first, last = months[0][0], months[-1][0]
    return QuestionAnswer(
        question=question, status=QuestionAnswerStatus.LIMITED, confidence=0.8, selected_tools=["period_average"],
        answer=(f"해석: ‘{word}’ → {topic}\n{scope}의 {source_label(topic)} {year}년 평균은 {shown}{_suffix(units)}입니다 "
                f"({first.month}월~{last.month}월, 월별 값 {len(values)}개의 단순 평균)."),
        evidence=[_evidence(cell) for cell in dict.fromkeys(cited)][:MAX_EVIDENCE],
        limitations=[f"질문의 표현을 원본 계열로 옮긴 해석(‘{word}’ → {topic})이 의도와 맞는지 확인해 주세요.",
                     "월별 값을 같은 비중으로 평균했습니다. 월별 분모를 반영한 가중 평균은 아닙니다."],
        verification=QuestionAnswerVerification(level="source_checked",
                                                checks=["source_values", "calculation", "period", "semantic_alias_resolved"]))
