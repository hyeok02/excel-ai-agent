"""Answer a value question when every best-matching source cell agrees.

Runs only after the regular paths could not answer (clarification, refusal or
a generated draft). It never picks one of several different values: a single
distinct value across all matching sources, at the newest common period when
no period is asked, is required. Otherwise the original answer stands.
"""
from app.agent.query.metric_observation_render import _period_label, _value
from app.agent.query.models import (
    QuestionAnswer, QuestionAnswerEvidence, QuestionAnswerStatus, QuestionAnswerVerification,
    QuestionVerificationLevel,
)
from app.agent.query.source_value_metrics import metric_values
from app.agent.query.source_value_tables import VETO, table_values
from app.agent.query.source_value_terms import question_terms
from app.services.provenance import EvidenceKind


def source_value_answer(question, summary, index):
    terms = question_terms(question)
    if terms is None or summary is None or index is None:
        return None
    records = table_values(terms, summary)
    if VETO in records:
        return None
    if records:
        best = max(item.rank for item in records)
        records = [item for item in records if item.rank == best]
    # Several copies of one time series: the newest row wins. Records selected
    # by a named row (a company, a device) must agree whatever their dates.
    series = [item for item in records if item.latest]
    if series:
        newest = max(item.period for item in series)
        records = [item for item in records if not item.latest or item.period == newest]
    metrics = metric_values(question, terms, index)
    values = {_normal(item.value) for item in records} | {_normal(item.value.value) for item, _ in metrics}
    units = {unit.identity for _, unit in metrics}
    if len(values) != 1 or len(units) > 1 or not (records or metrics):
        return None
    return _answer(question, records, metrics)


def _normal(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), 6)
    return " ".join(str(value).split()).casefold()


def _answer(question, records, metrics):
    if metrics:
        item, unit = metrics[0]
        shown = _value(item, unit)
        when = f" ({_period_label(item)})" if item.period.year > 1 else ""
        subject = f"‘{item.label.value}’"
    else:
        item = records[0]
        shown = _display(item.value, item.header)
        when = f" ({item.period.year}년 {item.period.month}월 {item.period.day}일 기준)" if item.period else ""
        subject = (f"‘{item.label}’의 ‘{item.header}’" if item.label else f"‘{item.header}’")
    places = len({(r.sheet, r.address) for r in records} | {item.value.reference for item, _ in metrics})
    text = f"{subject} 값은 {shown}입니다{when}."
    if places > 1:
        text += f" 같은 값이 원본 {places}곳에서 확인됩니다."
    return QuestionAnswer(
        question=question, answer=text, status=QuestionAnswerStatus.ANSWERED, confidence=0.9,
        selected_tools=["source_value_lookup"], evidence=_evidence(records, metrics), limitations=[],
        verification=QuestionAnswerVerification(level=QuestionVerificationLevel.SOURCE_CHECKED,
                                                checks=["cited_cells", "source_values"]),
    )


def _display(value, header):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return f"‘{' '.join(str(value).split())}’"
    text = f"{value:,.0f}" if float(value).is_integer() else f"{value:,.6f}".rstrip("0").rstrip(".")
    return text + ("%" if "%" in header else "")


def _evidence(records, metrics):
    cells = []
    for item in records:
        cells += [(item.sheet, item.address, item.value, "질문한 원본 값"),
                  (item.sheet, item.header_address.rsplit("!", 1)[-1], item.header, "원본 항목명")]
        if item.label_address:
            cells.append((item.sheet, item.label_address, item.label, "원본 행 이름"))
    for item, _ in metrics:
        cells += [(cell.sheet_name, cell.address, cell.value, text) for cell, text in (
            (item.value, "질문한 원본 값"), (item.label, "원본 항목명"), (item.period_cell, "원본 기준일"))
            if cell is not None and item.period.year > 1 or text != "원본 기준일"]
    return [QuestionAnswerEvidence(kind=EvidenceKind.CELL, sheet_name=sheet, reference=ref, value=value,
                                   description=text, label=text)
            for sheet, ref, value, text in dict.fromkeys((s, r, v, t) for s, r, v, t in cells
                                                         if not isinstance(v, (list, dict)))][:24]
