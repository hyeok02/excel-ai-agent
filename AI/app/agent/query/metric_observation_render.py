"""Render source-bound observations and preserve their evidence."""
import re
from dataclasses import asdict, replace
from decimal import Decimal
from app.agent.query.comparison_value_format import comparison_values
from app.agent.query.excel_number_formats import display_value, parse_number_format
from app.agent.query.metric_observation_units import observation_unit
from app.agent.query.metric_observation_periods import source_period_grain
from app.agent.query.metric_observations import _normal
from app.agent.query.models import QuestionAnswer, QuestionAnswerEvidence, QuestionAnswerStatus
_GRAIN_NAMES = {"annual": "회계연도", "quarter": "분기", "month": "월간", "ltm": "최근 12개월"}
_SCENARIO_NAMES = {"actual": "실적", "estimate": "예상", "budget": "예산"}

def _unique(candidates, rows):
    if not candidates:
        return None
    identities = {(item.period, item.grain, item.scenario, item.value.value,
                   observation_unit(item, rows).identity) for item in candidates}
    if len(identities) != 1:
        # Duplicate copies with absent versus explicit actual labels are safe
        # only when their dates, reporting grains, units and values all agree.
        without_scenario = {(item.period, item.grain, item.value.value,
                             observation_unit(item, rows).identity) for item in candidates}
        if len(without_scenario) != 1 or any(item.scenario not in {None, "actual"} for item in candidates):
            return None
    return max(candidates, key=lambda item: len(item.context_cells) + len(item.entity_cells))

def _render(selected, units, compare):
    header = str(selected[0].label.value)
    if not compare:
        lines = [f"{_period_label(item)} {header}: {_value(item, unit)}" for item, unit in zip(selected, units)]
        return "\n".join(lines) + "."
    start, end = selected
    change = Decimal(str(end.value.value)) - Decimal(str(start.value.value))
    before, after, moved = comparison_values(
        start.value.value, end.value.value, float(change),
        start.value.number_format, end.value.number_format, units[0].suffix,
    )
    verb = "증가" if change > 0 else "감소" if change < 0 else "변동 없음"
    share = ""
    if start.value.value and not parse_number_format(start.value.number_format).percent:
        rate = abs(change) / abs(Decimal(str(start.value.value))) * 100
        share = f" ({rate:.4f}%)"
    text = f"{header}: {_period_label(start)} {before}에서 {_period_label(end)} {after}으로 "
    text += f"{moved}{share} {verb}." if change else "변동이 없습니다."
    if start.grain != end.grain:
        text += " 연간·분기 등 집계 기간의 길이가 달라 성장률로 해석하면 안 됩니다."
    if start.scenario != end.scenario and end.scenario == "estimate":
        text += " 종료 값은 실적이 아니라 원본에 표시된 예상치입니다."
    return text

def _value(item, unit):
    spec = parse_number_format(item.value.number_format)
    # General-format calculations can contain binary floating-point tails;
    # bounded presentation does not change the saved operands used in math.
    if spec.mode == "raw":
        spec = replace(spec, mode="", minimum_decimals=0, maximum_decimals=6)
    return display_value(item.value.value, spec, unit.suffix)

def _period_label(item):
    date = item.period
    text = f"{date.year}년 {date.month}월"
    if source_period_grain(item.period_cell.value) != "month":
        text += f" {date.day}일"
    parts = [_GRAIN_NAMES.get(item.grain), _SCENARIO_NAMES.get(item.scenario)]
    return text + (" " + " ".join(part for part in parts if part) if any(parts) else " 기준")

def _metric_identity(label):
    from app.agent.query.search_terms import SEMANTIC_ALIASES

    normal = _normal(re.sub(r"\([^)]*\)|\b(?:total|latest)\b", " ", str(label), flags=re.I))
    for concept, aliases in SEMANTIC_ALIASES.items():
        if normal in {_normal(value) for value in (concept, *aliases)}:
            return concept if concept != "인원" else "직원"
    return normal

def _evidence(cell):
    source = cell.evidence()
    return QuestionAnswerEvidence(
        **asdict(source), label=f"{cell.reference}: {str(cell.value)[:100]}",
    )

def _unavailable(question, reason):
    return QuestionAnswer(
        question=question, answer=reason, status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE,
        confidence=0, selected_tools=["bind_metric_observations"], evidence=[], limitations=[reason],
    )
