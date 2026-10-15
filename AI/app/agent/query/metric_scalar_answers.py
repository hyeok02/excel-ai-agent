"""Answer unambiguous source-labelled scalars without treating prose as a table."""

import re
from datetime import datetime
from app.agent.query.ambiguity_metric_scope import bind_explicit_metric_scope

from app.agent.query.metric_observation_answers import (
    _bind_entity_scope, _evidence, _multiple_named_metrics, _scope_references, _unavailable, _value,
)
from app.agent.query.metric_observation_periods import LATEST, requested_periods
from app.agent.query.metric_observation_units import observation_unit
from app.agent.query.metric_request_coverage import request_covered
from app.agent.query.metric_observations import (
    MetricObservation,
    _column,
    _human_label,
    _normal,
    _numeric,
    _sheet_rows,
    _text_in_question,
    metric_label_matches,
)
from app.agent.query.models import (
    QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification, QuestionVerificationLevel,
)

_BLOCKED = re.compile(
    r"비교|증감|변화|변동|추이|평균|합계|총합|항목별|부서별|직무별|몇\s*(?:건|개)|건수|개수|"
    r"제외|포함|이상|이하|미만|초과|조건|[<>]=?|"
    r"\b(?:compare|change|trend|average|mean|sum|count|how\s+many|by\s+department|"
    r"where|only|excluding|above|below)\b", re.I,
)


def metric_scalar_answer(question, summary, index, intent=None):
    """Only one distinctly labelled cell may satisfy an undated scalar request."""
    if _BLOCKED.search(question) or requested_periods(question) or LATEST.search(question):
        return None
    if intent is not None and (getattr(intent, "whole_workbook", False)
                               or getattr(intent, "kind", "other") not in {"cell_lookup", "other"}):
        return None
    rows = list(index.rows)
    names = {row.sheet_name for row in rows}
    named = {name for name in names if name.casefold() in question.casefold()}
    if named:
        rows = [row for row in rows if row.sheet_name in named]
    observations = []
    for sheet_rows in _sheet_rows(rows).values():
        for row in sheet_rows:
            labels = [cell for cell in row.cells if _human_label(cell)]
            for label in labels:
                if not metric_label_matches(str(label.value), question):
                    continue
                left = _column(label)
                right = min((_column(cell) for cell in labels if _column(cell) > left), default=16_385)
                numeric = [cell for cell in row.cells if left < _column(cell) < right and _numeric(cell.value)]
                record = _adjacent_record(sheet_rows, row, label, question)
                if record:
                    observations.append(record)
                elif len(numeric) == 1:
                    observations.append(MetricObservation(
                        label, numeric[0], datetime.min, label, None, None, (),
                    ))
    if not observations:
        return None
    observations, scope_question = bind_explicit_metric_scope(question, observations)
    observations = _bind_entity_scope(scope_question, observations, rows, named)
    if observations is None:
        return None
    if _multiple_named_metrics(question, observations):
        return _unavailable(question, "여러 항목의 값을 함께 지정했습니다. 각 항목을 구분해 조회해야 합니다.")
    records = [item for item in observations
               if re.search(r"\d+", item.label.address)[0] != re.search(r"\d+", item.value.address)[0]]
    if records:
        observations = records
    else:
        exact = [item for item in observations if _normal(str(item.label.value)) in _normal(question)]
        if exact:
            longest = max(len(_normal(str(item.label.value))) for item in exact)
            observations = [item for item in exact if len(_normal(str(item.label.value))) == longest]
    if index.truncated_for({item.value.sheet_name for item in observations}):
        return _unavailable(question, "원본 일부가 검색 범위를 넘어 동일 항목의 다른 값을 확인할 수 없습니다.")
    units = [observation_unit(item, rows) for item in observations]
    if any(unit.identity[0] == "conflicting_units" for unit in units):
        return _unavailable(question, "셀 표시 형식과 원본 단위 설명이 서로 달라 수치를 확정할 수 없습니다.")
    identities = {(item.value.value, unit.identity) for item, unit in zip(observations, units)}
    labels = {str(item.label.value).strip().lstrip("+-= ").casefold() for item in observations}
    if len(identities) != 1 or len(labels) != 1:
        return _unavailable(question, "같은 항목에 서로 다른 원본 값이 있어 시트나 기준일을 지정해야 합니다.")
    selected, unit = observations[0], units[0]
    scope = _scope_references(scope_question, [selected], rows, named)
    if scope is None:
        return None
    if not request_covered(scope_question, [selected], named):
        return _unavailable(question, "추가로 지정한 항목·조건·단위 변환까지 원본에 연결하지 못했습니다.")
    references = [*scope, selected.label, selected.value, *selected.context_cells,
                  *selected.entity_cells, *unit.references]
    evidence = [_evidence(cell) for cell in dict.fromkeys(references)]
    entity = " ".join(str(cell.value) for cell in selected.entity_cells)
    subject = f"{entity}의 " if entity else ""
    subject += str(selected.label.value).strip().lstrip("+-= ")
    limitations = [] if unit.known else ["숫자는 원본 저장값 기준이며 별도 단위는 원본에서 확인되지 않았습니다."]
    return QuestionAnswer(
        question=question, answer=f"{subject}: {_value(selected, unit)}.",
        status=QuestionAnswerStatus.ANSWERED if not limitations else QuestionAnswerStatus.LIMITED,
        confidence=1.0 if not limitations else 0.9,
        selected_tools=["bind_metric_observations"], evidence=evidence, limitations=limitations,
        verification=QuestionAnswerVerification(
            level=QuestionVerificationLevel.REQUEST_CHECKED if unit.known else QuestionVerificationLevel.SOURCE_CHECKED,
            checks=["table_scope", "metric", "source_cells"] + (["unit"] if unit.known else []),
        ),
    )


def _adjacent_record(rows, row, label, question):
    if not _text_in_question(str(label.value), question):
        return None
    value = next((cell for cell in row.cells if _column(cell) == _column(label) + 1
                  and _numeric(cell.value)), None)
    if value is None:
        return None
    headers = [cell for previous in rows if 0 < row.row_number - previous.row_number <= 100
               for cell in previous.cells if _column(cell) == _column(value)
               and _human_label(cell) and metric_label_matches(str(cell.value), question)]
    if not headers:
        return None
    header = max(headers, key=lambda cell: int(re.search(r"\d+", cell.address)[0]))
    return MetricObservation(header, value, datetime.min, label, None, None, (), (label,))
