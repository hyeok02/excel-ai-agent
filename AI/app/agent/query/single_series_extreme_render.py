"""Render verified answers for one-series adjacent extrema."""
import re

from app.agent.query.ambiguity_candidates import AmbiguousCandidate
from app.agent.query.excel_number_formats import display_value, parse_number_format
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification
from app.agent.query.trend_calculations import decimal_value, exact_difference
from app.agent.query.trend_render import _movement, _period

_YEAR_ANSWER = re.compile(r"연도|년도|언제|시점|때|year|when", re.I)
_INTERVAL_ANSWER = re.compile(r"구간|기간|interval|period", re.I)


def render(question, candidate, units, points, winners, direction, annual):
    spec = parse_number_format(winners[0][1].value.number_format)
    unit = units[candidate.observations.index(winners[0][1])]
    lines = [f"원본 범위: {candidate.table_id}"]
    if candidate.period_note:
        lines.append(candidate.period_note)
    label = str(winners[0][0].label.value)
    for number, (before, after, _) in enumerate(winners, 1):
        before_number = decimal_value(before.value.value)
        after_number = decimal_value(after.value.value)
        before_value = display_value(before_number, spec, unit.suffix)
        after_value = display_value(after_number, spec, unit.suffix)
        moved = _difference(before_number, after_number, spec, unit)
        year_answer = _YEAR_ANSWER.search(question) and not _INTERVAL_ANSWER.search(question)
        statement = (
            f"{_period(after)}입니다({_period(before)} 대비)" if year_answer
            else f"{_period(before)} → {_period(after)}입니다"
        )
        prefix = f"{number}. " if len(winners) > 1 else ""
        lines.append(
            f"{prefix}{label}의 연도별 값이 가장 많이 "
            f"{'증가한' if direction == 'increase' else '감소한'} "
            f"{'연도는' if year_answer else '구간은'} {statement}. "
            f"{before_value} → {after_value}, {moved}."
        )
    if len(winners) > 1:
        lines.append(f"같은 최대 {'증가' if direction == 'increase' else '감소'}폭의 구간이 {len(winners)}개입니다.")
    return _answer(question, candidate, units, points, "\n".join(lines), annual)


def _difference(before, after, spec, unit):
    if spec.percent or unit.suffix == "%":
        difference = exact_difference(before, after)
        moved = display_value(difference.copy_abs(), spec).removesuffix("%")
        return f"{moved}%p {'증가' if difference > 0 else '감소'}"
    return _movement(before, after, spec, unit)


def _answer(question, candidate, units, points, text, annual):
    limitations = []
    if not all(unit.known for unit in units):
        limitations.append("수치는 원본 저장값 기준입니다. 통화·수량 단위까지는 확정하지 못했습니다.")
    if candidate.hidden_rows:
        limitations.append(f"숨겨진 {candidate.hidden_rows}개 행을 제외한 표시 데이터의 계산입니다.")
    checks = ["table_scope", "metric", "complete_series", "source_values",
              "chronological_order", "adjacent_difference", "maximum_change", "all_ties",
              "request_alignment"]
    if annual:
        checks.append("annual_cadence")
    if all(unit.known for unit in units):
        checks.append("unit")
    return QuestionAnswer(
        question=question, answer=text, status="limited" if limitations else "answered",
        confidence=0.9 if limitations else 1,
        selected_tools=["chronological_interval_extreme"],
        evidence=[_evidence(cell) for cell in _references(candidate, units, points)],
        limitations=limitations,
        verification=QuestionAnswerVerification(
            level="source_checked" if limitations else "request_checked", checks=checks,
        ),
    )


def checked_no_movement(question, candidate, units, points, movement):
    return QuestionAnswer(
        question=question,
        answer=f"원본 범위: {candidate.table_id}\n확인한 전체 기간에는 값이 {movement}한 인접 구간이 없습니다.",
        status="answered", confidence=1, selected_tools=["chronological_interval_extreme"],
        evidence=[_evidence(cell) for cell in _references(candidate, units, points)],
        limitations=[],
        verification=QuestionAnswerVerification(
            level="request_checked",
            checks=["table_scope", "metric", "complete_series", "source_values",
                    "chronological_order", "adjacent_difference", "request_alignment"],
        ),
    )


def _references(candidate, units, points):
    references = [*candidate.context]
    for point, unit in zip(points, units):
        references.extend((point.label, point.period_cell, point.value, *point.context_cells,
                           *point.entity_cells, *point.unit_context, *unit.references))
    return dict.fromkeys(references)


def choice(question, candidate):
    point = candidate.observations[0]
    sheet = point.value.sheet_name.replace("'", "''")
    reference = candidate.table_id.rpartition("!")[2]
    first, last = _period(candidate.observations[0]), _period(candidate.observations[-1])
    label = str(point.label.value)
    return AmbiguousCandidate(
        label=label, scope=candidate.table_id,
        details=f"{first}~{last}, {len(candidate.observations)}개 시점의 원본 값",
        followup=f"'{sheet}'!{reference} 범위의 {label} 기준으로: {question}",
        cells=tuple(dict.fromkeys((point.label, point.period_cell, point.value, *candidate.context))),
    )


def unavailable(question, reason):
    return QuestionAnswer(
        question=question, answer=reason, status="insufficient_evidence", confidence=0,
        selected_tools=["chronological_interval_extreme"], evidence=[], limitations=[reason],
    )
