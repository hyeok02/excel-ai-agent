"""Answer a whole-history trend when every matching source series agrees.

Runs only after the chronological trend path could not connect a date axis.
Each matching label row on a period axis is one series; estimates are left
out and said so. All series must agree wherever their periods overlap, one of
them must cover every period the others have, and its periods must be evenly
spaced (a skipped year is a gap, not a trend). Otherwise the refusal stands.
"""
import re

from app.agent.query.metric_observation_render import _period_label, _value
from app.agent.query.metric_observation_units import observation_unit
from app.agent.query.models import (
    QuestionAnswer, QuestionAnswerEvidence, QuestionAnswerStatus, QuestionAnswerVerification,
    QuestionVerificationLevel,
)
from app.agent.query.source_value_metrics import matching_observations
from app.agent.query.source_value_terms import question_terms
from app.agent.query.trend_request import asks_trend
from app.services.provenance import EvidenceKind

_TREND_WORDS = re.compile(r"추이|흐름|변화|변동|\btrend\b", re.I)
_PLAIN_TREND = re.compile(r"^\s*\S+(?:\s+\S+)?\s*(?:추이|흐름|변화|변동)(?:는|은|를|가)?\s*(?:알려줘|보여줘|어때|어떻게 돼)?\s*[?.]?\s*$")
MAX_LISTED = 12


def source_series_answer(question, summary, index):
    if summary is None or index is None or not asks_trend(question) or not _PLAIN_TREND.match(question):
        return None
    terms = question_terms(_TREND_WORDS.sub(" ", question))
    if terms is None or terms[0] is not None:
        return None
    found, rows = matching_observations(question, terms, index)
    actual = [item for item in found if item.scenario not in {"estimate", "budget"}]
    annual = [item for item in actual if item.grain in {"annual", None} and item.period.year > 1]
    if not annual or not any(item.grain == "annual" for item in actual) and len(annual) != len(actual):
        return None
    series = {}
    for item in annual:
        key = (item.label.reference, tuple(cell.value for cell in item.entity_cells))
        points = series.setdefault(key, {})
        if item.period in points and _normal(points[item.period].value.value) != _normal(item.value.value):
            return None
        points.setdefault(item.period, item)
    series = _without_growth_copies(series)
    if not _compatible({observation_unit(item, rows) for points in series.values() for item in points.values()}):
        return None
    merged = {}
    for points in series.values():
        for period, item in points.items():
            if merged.setdefault(period, _normal(item.value.value)) != _normal(item.value.value):
                return None
    complete = [points for points in series.values() if set(points) == set(merged)]
    if not complete or len(merged) < 2 or not _even(sorted(merged)):
        return None
    chosen = [complete[0][period] for period in sorted(merged)]
    return _answer(question, chosen, rows, len(series), len(actual) != len(found))


def _without_growth_copies(series):
    """A row whose values are another row's period-over-period growth is not that metric."""
    growth = []
    for points in series.values():
        periods = sorted(points)
        growth.append({later: float(points[later].value.value) / float(points[earlier].value.value) - 1
                       for earlier, later in zip(periods, periods[1:]) if float(points[earlier].value.value)})
    kept = {}
    for key, points in series.items():
        if not any(sum(period in rates and _is_rate(float(item.value.value), rates[period])
                       for period, item in points.items()) >= 2 for rates in growth):
            kept[key] = points
    return kept


def _is_rate(value, rate):
    return abs(value - rate) < 0.00005 or abs(value - rate * 100) < 0.005


def _compatible(units):
    """One unit, or one currency written with and without its country ("달러", "미국 달러")."""
    shapes = {unit.identity[1:] for unit in units}
    suffixes = sorted({unit.suffix for unit in units}, key=len)
    return (all(unit.known for unit in units) and len(shapes) == 1
            and all(suffix.split()[-1:] == suffixes[-1].split()[-1:]
                    and set(suffix.split()) <= set(suffixes[-1].split()) for suffix in suffixes))


def _even(periods):
    gaps = [(later - earlier).days for earlier, later in zip(periods, periods[1:])]
    return max(gaps) - min(gaps) <= 7 and 300 <= min(gaps) <= 400


def _normal(value):
    return round(float(value), 6)


def _answer(question, points, rows, copies, estimates):
    unit = observation_unit(points[0], rows)
    shown = [(_period_label(item), _value(item, unit)) for item in points]
    listed = shown if len(shown) <= MAX_LISTED else [shown[0], ("…", "…"), shown[-1]]
    first, last = float(points[0].value.value), float(points[-1].value.value)
    change = last - first
    direction = "증가" if change > 0 else "감소" if change < 0 else "변동 없음"
    rate = f"({abs(change) / abs(first) * 100:.2f}%) " if first and change else ""
    text = (f"‘{points[0].label.value}’ 추이: " + " → ".join(f"{when} {value}" for when, value in listed)
            + f". 첫 기간보다 {_amount(abs(change))}{unit.suffix} {rate}{direction}" + ("했습니다." if change else "입니다."))
    if copies > 1:
        text += f" 겹치는 기간의 값은 원본 {copies}곳에서 모두 일치합니다."
    limitations = ["원본의 예상치 기간은 실적 추이에서 제외했습니다."] if estimates else []
    cells = [(cell, text) for item in points for cell, text in (
        (item.value, "원본 값"), (item.period_cell, "원본 기준일"))] + [(points[0].label, "원본 항목명")]
    return QuestionAnswer(
        question=question, answer=text, confidence=0.9,
        status=QuestionAnswerStatus.LIMITED if limitations else QuestionAnswerStatus.ANSWERED,
        selected_tools=["source_series_lookup"], limitations=limitations,
        evidence=[QuestionAnswerEvidence(kind=EvidenceKind.CELL, sheet_name=cell.sheet_name, reference=cell.address,
                                         value=cell.value, description=text, label=text)
                  for cell, text in dict.fromkeys(cells) if not isinstance(cell.value, (list, dict))],
        verification=QuestionAnswerVerification(level=QuestionVerificationLevel.SOURCE_CHECKED,
                                                checks=["cited_cells", "source_values", "complete_series"]),
    )


def _amount(value):
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"
