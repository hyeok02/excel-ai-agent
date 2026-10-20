"""Bind row-level unit and scenario controls to original table headers."""
from app.agent.query.metric_observation_periods import qualifier, SCENARIOS

UNIT_HEADERS = {"currency": "currency", "통화": "currency", "magnitude": "magnitude", "금액 단위": "magnitude"}
_SCENARIO_HEADERS = {"scenario", "시나리오", "실적/예상", "실적/예산"}


def row_unit_context(headers, row):
    result = []
    for key, header in headers.items():
        if str(header.value).strip().casefold() in UNIT_HEADERS:
            result.append(header)
            if row.get(key) is not None:
                result.append(row[key])
    return tuple(result)


def row_scenario(headers, row, dated_scenario):
    scenarios = {dated_scenario} if dated_scenario else set()
    for key, header in headers.items():
        if str(header.value).strip().casefold() in _SCENARIO_HEADERS and row.get(key):
            if scenario := qualifier(row[key].value, SCENARIOS):
                scenarios.add(scenario)
    if len(scenarios) > 1:
        raise ValueError("날짜와 행의 실적·예상 구분이 서로 충돌합니다.")
    return next(iter(scenarios), None)
