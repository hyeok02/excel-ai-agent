"""Answer explicit reporting periods from uniquely bound source observations."""
import re
from app.agent.query.ambiguity_metric_scope import bind_explicit_metric_scope
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.metric_observation_periods import LATEST, requested_periods
from app.agent.query.metric_observation_units import observation_unit
from app.agent.query.metric_request_coverage import request_covered
from app.agent.query.metric_observations import _normal, dated_record_observations, horizontal_observations
from app.agent.query.metric_observation_scope import _bind_entity_scope
from app.agent.query.metric_observation_guards import _scope_references, _multiple_named_metrics
from app.agent.query.metric_observation_render import _unique, _render, _metric_identity, _evidence, _unavailable, _value
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification, QuestionVerificationLevel
_UNSUPPORTED = re.compile(
    r"항목별|부서별|직무별|각\s*(?:부서|직무|항목)|평균|중앙값|표준편차|합계|총합|"
    r"제외|포함|이상|이하|미만|초과|조건|지역별|[<>]=?|"
    r"\b(?:average|mean|median|sum|maximum|minimum|highest|lowest|by\s+department|"
    r"only|where|excluding|above|below)\b", re.I,
)
_CHANGE = re.compile(r"증가|감소|증감|변화|변동|얼마나|차이|비교|\b(?:change|growth|difference|compare)\b", re.I)


def metric_observation_answer(question, summary, index: WorkbookDataIndex, intent=None) -> QuestionAnswer | None:
    requests = requested_periods(question)
    latest = bool(LATEST.search(question))
    if not (requests or latest) or _UNSUPPORTED.search(question):
        return None
    if intent is not None and (getattr(intent, "whole_workbook", False)
                               or getattr(intent, "kind", "other") not in {"cell_lookup", "comparison", "other"}):
        return None
    if len(requests) > 4:
        return None
    rows = list(index.rows)
    sheet_names = {row.sheet_name for row in rows}
    named_sheets = {name for name in sheet_names if name.casefold() in question.casefold()}
    if named_sheets:
        rows = [row for row in rows if row.sheet_name in named_sheets]
    observations = horizontal_observations(rows, question)
    if latest:
        observations.extend(dated_record_observations(rows, question))
    if not observations:
        return None
    observations, scope_question = bind_explicit_metric_scope(question, observations)
    observations = _bind_entity_scope(scope_question, observations, rows, named_sheets)
    if observations is None:
        return _unavailable(question, "질문에 지정한 대상과 원본 표의 대상을 연결할 수 없습니다.")
    if _multiple_named_metrics(question, observations):
        return _unavailable(question, "서로 다른 항목을 함께 지정했습니다. 각 항목과 기간을 나누어 확인해야 합니다.")
    exact = [item for item in observations if _normal(str(item.label.value)) in _normal(question)]
    if exact:
        longest = max(len(_normal(str(item.label.value))) for item in exact)
        observations = [item for item in exact if len(_normal(str(item.label.value))) == longest]
    # Naming two separate measures is not a request for one measure's change.
    labels = {_metric_identity(item.label.value) for item in observations}
    if len(labels) != 1:
        return None
    if index.truncated_for({item.value.sheet_name for item in observations}):
        return _unavailable(question, "관련 원본 범위가 검색 한도를 넘어 전체 기간을 확인할 수 없습니다.")
    selected = []
    if latest and not requests:
        current = [item for item in observations if item.scenario not in {"estimate", "budget"}]
        if not current:
            return _unavailable(question, "저장된 원본에서 실적의 최신 기준일을 확인하지 못했습니다.")
        newest = max(item.period for item in current)
        match = _unique([item for item in current if item.period == newest], rows)
        if match is None:
            return _unavailable(question, "같은 최신 기준일의 값 또는 기간 구분이 서로 달라 하나로 확정할 수 없습니다.")
        selected.append(match)
    else:
        for request in requests:
            candidates = [item for item in observations
                          if request.matches(item.period, item.grain, item.scenario)]
            # A bare reporting year denotes an annual column when the source
            # explicitly has one. Never select a quarter or LTM by column order.
            if request.grain is None and request.month is None:
                annual = [item for item in candidates if item.grain == "annual"]
                candidates = annual or candidates
            if request.scenario is None:
                actual = [item for item in candidates if item.scenario == "actual"]
                candidates = actual or candidates
            match = _unique(candidates, rows)
            if match is None:
                return _unavailable(question, "질문한 기간·연간/분기·실적/예상 구분에 맞는 원본 값을 하나로 확정할 수 없습니다.")
            selected.append(match)
    if any(item.value.value is None for item in selected):
        return _unavailable(question, "해당 기간의 수식에 저장된 계산 결과가 없어 값을 확인할 수 없습니다.")
    scope = _scope_references(scope_question, selected, rows, named_sheets)
    if scope is None:
        return _unavailable(question, "질문에 지정한 대상과 원본 표의 대상을 연결할 수 없습니다.")
    if not request_covered(scope_question, selected, named_sheets):
        return _unavailable(question, "추가로 지정한 항목·조건·단위 변환까지 원본에 연결하지 못했습니다.")
    units = [observation_unit(item, rows) for item in selected]
    if any(unit.identity[0] == "conflicting_units" for unit in units):
        return _unavailable(question, "셀 표시 형식과 원본 단위 설명이 서로 달라 수치를 확정할 수 없습니다.")
    if len({unit.identity for unit in units}) != 1:
        return _unavailable(question, "선택한 기간의 원본 단위가 달라 동일 단위의 비교를 확인할 수 없습니다.")
    comparisons = len(selected) == 2 and bool(_CHANGE.search(question))
    text = _render(selected, units, comparisons)
    references = [*scope]
    for item, unit in zip(selected, units):
        references.extend((item.label, item.value, item.period_cell, *item.context_cells,
                           *item.entity_cells, *unit.references))
    evidence = [_evidence(cell) for cell in dict.fromkeys(references)]
    limitations = []
    if not all(unit.known for unit in units):
        limitations.append("숫자는 원본 저장값 기준이며 통화·수량 단위를 명시한 근거는 확인되지 않았습니다.")
    return QuestionAnswer(
        question=question, answer=text,
        status=QuestionAnswerStatus.LIMITED if limitations else QuestionAnswerStatus.ANSWERED,
        confidence=1.0 if not limitations else 0.9,
        selected_tools=["bind_metric_observations"], evidence=evidence, limitations=limitations,
        verification=QuestionAnswerVerification(
            level=QuestionVerificationLevel.REQUEST_CHECKED if not limitations else QuestionVerificationLevel.SOURCE_CHECKED,
            checks=["table_scope", "metric", "period", "scenario", "source_cells"]
                   + (["unit"] if not limitations else [])
                   + (["calculation"] if comparisons else []),
        ),
    )
