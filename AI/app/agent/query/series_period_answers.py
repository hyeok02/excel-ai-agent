"""Two years' change, or the highest or lowest year, of a series the plan route could not bind.

"2020년 대비 2025년 석탄 발전량 변화는?" and "천연가스 발전량이 가장 많았던 해는?" read Table_1_01's
annual section, as "2025년 총발전량은?" does: the word is read among the series names, the annual
rows come first and partial bases (year to date, rolling) never stand in. The years compared,
or every annual value ranked, are source cells, each cited; the reading is stated.
"""
import re

from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.references import normalize_reference
from app.agent.query.series_topic_names import named_topic, series_words
from app.agent.query.series_value_answers import MAX_TOPICS, _YEAR
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

_CHANGE = re.compile(r"대비|부터|에서|변화|차이|증감|늘었|줄었|증가|감소|올랐|내렸")
_HIGH = re.compile(r"가장\s*(?:많|높|컸|큰)|제일\s*(?:많|높|컸|큰)|최대|최고")
_LOW = re.compile(r"가장\s*(?:적|낮|작)|제일\s*(?:적|낮|작)|최소|최저")
_WHEN = re.compile(r"해|연도|년도|언제|시점|때")


def series_period_answer(question, summary, index, resolver=None):
    years = sorted({int(year) for year in _YEAR.findall(question)})
    high, low = bool(_HIGH.search(question)), bool(_LOW.search(question))
    change = len(years) == 2 and _CHANGE.search(question) and not (high or low)
    extreme = not years and high != low and _WHEN.search(question)
    if summary is None or index is None:
        return None
    if len(years) == 1 and high != low:  # "2024년 발전량이 가장 많은 에너지원": the year's series compared
        return _cross_series(question, summary, index, years[0], high, resolver)
    if not (change or extreme):
        return None
    found = _annual_points(question, summary, resolver)
    if found is None:
        return None
    word, topic, sheet, section, section_cell, points, unit_note = found
    if change:
        chosen = [points.get(year) for year in years]
        if None in chosen:
            return None
        (_, older, old), (_, newer, new) = chosen
        delta = new["value"] - old["value"]
        units = unit(new) or (source_unit(unit_note["value"]) if unit_note else "")
        shown = lambda value: displayed_text(value, displayed_value(value)) + _suffix(units)
        moved = "변화가 없습니다" if delta == 0 else (
            f"{abs(round(delta, 10)):,g}{_suffix(units)}" + (f"({abs(delta) / abs(old['value']) * 100:.2f}%)" if old["value"] else "")
            + (" 증가했습니다" if delta > 0 else " 감소했습니다"))
        body = f"{years[0]}년 {shown(old)} → {years[1]}년 {shown(new)}, {moved}."
        used = [cell for item in chosen for cell in item[1:]]
    else:
        best = (max if high else min)(points.items(), key=lambda item: item[1][2]["value"])
        ties = [year for year, item in points.items() if item[2]["value"] == best[1][2]["value"]]
        if len(ties) != 1:
            return None  # a tie is not decided by row order
        units = unit(best[1][2]) or (source_unit(unit_note["value"]) if unit_note else "")
        body = (f"{'가장 높았던' if high else '가장 낮았던'} 해는 {best[0]}년 "
                f"{displayed_text(best[1][2], displayed_value(best[1][2]))}{_suffix(units)}입니다 (연간 값 {len(points)}개 비교).")
        used = [cell for item in points.values() for cell in item[1:]]
    header = next(item[0] for item in points.values())
    references = [reference(sheet, item["cell"]) for item in (header, header.get("_parent"), section_cell, *used) if item]
    cells = {normalize_reference(cell.reference): cell for row in index.rows for cell in row.cells}
    cited = [cells.get(normalize_reference(item)) for item in references]
    if None in cited:
        return None
    scope = " · ".join(part for part in (sheet, section) if part)
    return QuestionAnswer(
        question=question, status=QuestionAnswerStatus.LIMITED, confidence=0.8, selected_tools=["verified_series"],
        answer=f"해석: ‘{word}’ → {topic}\n{scope}의 {source_label(topic)}: {body}",
        evidence=[_evidence(cell) for cell in dict.fromkeys(cited)],
        limitations=[f"질문의 표현을 원본 계열로 옮긴 해석(‘{word}’ → {topic})이 의도와 맞는지 확인해 주세요."],
        verification=QuestionAnswerVerification(level="source_checked",
                                                checks=["source_values", "calculation", "semantic_alias_resolved"]))


def _annual_points(question, summary, resolver):
    """(word, topic, sheet, section, section cell, {year: (header, period, value)}, unit note) of one annual series."""
    context = build_workbook_context(summary)
    topics = list(dict.fromkeys(str(item.topic) for _, item in all_series_facts(context) if item.topic))[:MAX_TOPICS]
    found = named_topic(series_words(question), topics, resolver)
    if found is None or found[1] is None:
        return None
    word, topic, _ = found
    sections = []
    for sheet in context.get("sheets", []):
        for header, section, section_cell, records, unit_note in (_series(sheet) if isinstance(sheet, dict) else ()):
            priority = _basis_priority(section)
            if priority in (1, 3) or len({record[0].year for record in records}) != len(records):
                continue  # a partial basis, or not one row per year
            for cell in header[1:]:
                points = {record[0].year: (cell, record[1], record[2].get(column(cell), {})) for record in records}
                points = {year: item for year, item in points.items() if finite(item[2].get("value"))}
                if metric_name(cell) == topic and len(points) >= 2:
                    sections.append((priority, sheet.get("name", ""), section, section_cell, points, unit_note))
    if not sections:
        return None
    best = [item for item in sections if item[0] == min(item[0] for item in sections)]
    if len(best) != 1:
        return None  # two annual tables of the same series: not one reading
    _, sheet, section, section_cell, points, unit_note = best[0]
    return word, topic, sheet, section, section_cell, points, unit_note


def _cross_series(question, summary, index, year, high, resolver):
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
