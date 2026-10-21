"""Calculate joined trajectories only after exact keys and full provenance bind."""
from dataclasses import replace

from app.agent.query.grouped_trend_answers import _answer
from app.agent.query.grouped_trend_scope import scoped_records
from app.agent.query.grouped_trend_series import grouped_series
from app.agent.query.joined_trend_binding import asks_joined_trend
from app.agent.query.joined_trend_sources import joined_trend_sources
from app.agent.query.joined_trend_composed import composed_joined_answer
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer
from app.agent.query.trend_request import trend_request_error


def joined_trend_answer(question, summary, index):
    if not asks_joined_trend(question, summary, index):
        return None
    try:
        source, named, references = joined_trend_sources(question, summary, index)
        composed = composed_joined_answer(question, source, named, index, summary)
        if composed is not None:
            return joined_evidence(composed, references, source)
        records, note, error = scoped_records(source.records, source.request, source.table,
                                              source.headers[source.metric.id], source.date.id, named)
        if error:
            raise ValueError("연결한 이력의 날짜 범위를 확정하지 못했습니다: " + error)
        if not records:
            raise ValueError("요청한 조건·날짜에 해당하는 연결 이력이 없습니다.")
        source = replace(source, records=tuple(records), note=note)
        series = grouped_series(source, index)
        for _, candidate, _, _ in series:
            if error := trend_request_error(source.request.residual, candidate.observations, named):
                raise ValueError(error)
        answer = _answer(question, source, series)
        return joined_evidence(answer, references, source)
    except (ValueError, TypeError, ArithmeticError) as error:
        reason = str(error) if isinstance(error, ValueError) else "표 연결 추이를 원본과 대조하지 못했습니다."
        return QuestionAnswer(question=question, answer=reason, status="insufficient_evidence", confidence=0,
                              selected_tools=["chronological_trend", "joined_trend"], limitations=[reason], evidence=[])


def joined_evidence(answer, references, source):
    answer.selected_tools.append("joined_trend")
    answer.verification.checks.extend(["typed_join_keys", "many_to_one_cardinality", "complete_join_coverage"])
    seen = {(cell.sheet_name, cell.reference) for cell in answer.evidence}
    answer.evidence.extend(_evidence(cell) for cell in references if (cell.sheet_name, cell.address) not in seen)
    if answer.status in {"answered", "limited"}:
        answer.answer = source.join_note + "\n\n" + answer.answer
        if not source.explicit_keys or source.metadata_dates:
            answer.status = "limited"
            answer.confidence = min(answer.confidence, 0.9)
            answer.verification.level = "source_checked"
            answer.verification.checks = [check for check in answer.verification.checks if check != "request_alignment"]
        if not source.explicit_keys:
            answer.limitations.append("연결 키가 질문에 명시되지 않아 유일한 같은 이름의 열을 후보 기준으로 사용했습니다. "
                                      "이 연결 기준이 맞는지 확인해 주세요. 연결 의도까지 확인된 답은 아닙니다.")
        if source.metadata_dates:
            unused = ", ".join(source.metadata_dates)
            answer.answer += f"\n\n추이·연결 기준으로 사용하지 않은 기준표 날짜: {unused}."
            answer.limitations.append(f"기준표의 {unused}는 추이·연결 날짜로 사용하지 않았습니다. "
                                      "과거 시점에도 기준표의 구분 정보가 유효했는지는 확인하지 않았습니다.")
    return answer
