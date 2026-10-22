"""Do not consume a named subgroup restriction as merely a matching label."""
import re

from app.agent.query.comparison_scope import GROUP_ALIASES
from app.agent.query.metric_observation_periods import SCENARIOS
from app.agent.query.metric_request_coverage import _remove_source_phrase
from app.agent.query.metric_observation_cells import _korean_metric_in_question
from app.agent.query.comparison_value_format import people_unit
from app.agent.query.excel_number_formats import parse_number_format


def group_restriction_error(question, series, group):
    labels = {str(candidate.observations[0].label.value) for candidate, _ in series}
    group_words = "|".join(map(re.escape, sorted(GROUP_ALIASES.get(group, {"항목", "metric"}), key=len, reverse=True)))
    for label in labels:
        for match in re.finditer(r"(?<!\w)" + re.escape(label) + r"(?![a-z0-9])", question, re.I):
            before, after = question[:match.start()], question[match.end():]
            if re.match(r"\s*(?:" + group_words + r")?\s*(?:만|제외|빼고|아닌|외의|포함)", after, re.I) \
                    or re.search(r"\b(?:only|excluding|except)\s*$", before, re.I):
                return "특정 부서·직무·항목만 선택하거나 제외한 순위는 선택 범위를 확정해야 합니다. 전체 항목 비교로 대신하지 않았습니다."
    return None


def scenario_request_error(question, series):
    text = question
    for label in {str(candidate.observations[0].label.value) for candidate, _ in series}:
        text = _remove_source_phrase(text, label)
    requested = {kind for kind, pattern in SCENARIOS.items() if pattern.search(text)}
    actual = {point.scenario for candidate, _ in series for point in candidate.observations}
    if requested and requested != actual:
        return "요청한 실적·예상·예산 구분을 원본 값에서 확인하지 못했습니다. 다른 시나리오의 값으로 대신하지 않았습니다."
    return None


def metric_unit_request_error(question, series):
    requested_people = bool(people_unit(question, ""))
    other_quantity = any(_korean_metric_in_question(noun, question) for noun in ("금액", "사용량"))
    for candidate, units in series:
        for point, unit in zip(candidate.observations, units):
            counted_people = bool(people_unit("", unit.suffix + " "
                                  + parse_number_format(point.value.number_format).suffix))
            if unit.known and ((requested_people and not counted_people) or (other_quantity and counted_people)):
                return "요청한 지표와 원본 값의 수량·통화·비율 단위가 달라 대신 답하지 않았습니다."
    return None
