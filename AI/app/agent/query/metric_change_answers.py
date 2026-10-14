"""이름을 댄 항목 하나의 변화를 코드가 직접 문장으로 만든다.

"서비스 부서 인원 알려줘", "전체 직원 수 어떻게 변했어?"는 모델이 쓰면 시작과
끝 값을 다른 행에서 집어 오기 쉽고, 그러면 검증에서 답변이 통째로 버려진다.
비교 도구가 이미 계산해 둔 값을 그대로 읽어 쓴다.
"""
from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.comparison_evidence import (
    available_evidence,
    comparison_change_matches,
    comparison_number,
    comparison_period,
    comparison_values_match,
    matched_comparison_evidence,
    present_comparison_evidence,
)
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus
from app.services.insights.display.glossary import readable
from app.services.insights.narratives.narrative_values import topic_particle

COUNTED_GROUPS = {"department", "role"}
MAX_NAMED = 8
# 사람 수를 세는 지표에는 '명'을 붙인다. 표기용이며 경로 선택과는 무관하다.
COUNTED_WORDS = ("명", "인원", "직원", "employee", "headcount", "staff")


def validated_metric_change_answer(
    question: str,
    execution: AgentExecution,
    index_truncated: bool,
    available: dict[str, object] | None = None,
) -> QuestionAnswer | None:
    if counted := _counted_answer(question, execution, index_truncated, available):
        return counted
    found = _metric_change(execution)
    if found is None:
        return None
    if not comparison_change_matches(
        found["start_value"], found["end_value"], found["change"]
    ):
        return None
    references = [
        *found["header_references"],
        *found.get("period_references", []),
        found["start_reference"],
        found["end_reference"],
    ]
    checks = (
        (found["start_reference"], found["start_value"]),
        (found["end_reference"], found["end_value"]),
    )
    return _answered(
        question, execution, index_truncated, available,
        _text(question, found), references, checks,
    )


def _answered(question, execution, index_truncated, available, text, references, checks):
    available = available if available is not None else available_evidence(execution)
    evidence, missing = matched_comparison_evidence(references, available)
    if not evidence or missing or not comparison_values_match(checks, available):
        return None
    limitations = []
    if index_truncated:
        limitations.append("대용량 워크북의 일부 관련 셀은 검색 범위에서 제외되었습니다.")
    failed = any(step.status is AgentStepStatus.FAILED for step in execution.steps)
    if failed:
        limitations.append("일부 Agent Tool 실행에 실패했습니다.")
    return QuestionAnswer(
        question=question,
        answer=text,
        status=QuestionAnswerStatus.LIMITED if limitations else QuestionAnswerStatus.ANSWERED,
        # 검색 범위가 잘려도 값 자체는 원본 셀에서 확인했다. 도구가 실패한
        # 경우에만 크게 낮춘다.
        confidence=0.7 if failed else (0.93 if limitations else 1.0),
        selected_tools=[step.tool_name for step in execution.steps],
        evidence=[present_comparison_evidence(item) for item in evidence],
        limitations=limitations,
    )


def _step_data(execution: AgentExecution, key: str, required: str) -> dict | None:
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        found = step.result.data.get(key)
        if isinstance(found, dict) and found.get(required):
            return found
    return None


def _text(question: str, found: dict) -> str:
    unit = _unit(question, found)
    change = float(found["change"])
    verb = "감소" if change < 0 else "증가"
    start = comparison_number(found["start_value"], unit)
    end = comparison_number(found["end_value"], unit)
    moved = comparison_number(abs(change), unit)
    period = (
        f"{comparison_period(found.get('start_date'))}부터 "
        f"{comparison_period(found.get('end_date'))}까지 "
        if found.get("start_date") and found.get("end_date")
        else ""
    )
    share = _share(found["start_value"], change)
    subject = readable(found["header"])
    return (
        f"{period}{subject}{topic_particle(subject)} "
        f"{start}에서 {end}으로 {moved}{share} {verb}했습니다."
    )


def _unit(question: str, found: dict) -> str:
    if found.get("metric_group") in COUNTED_GROUPS:
        return "명"
    asked = f"{question} {found['header']}".casefold()
    return "명" if any(word in asked for word in COUNTED_WORDS) else ""


def _share(start: object, change: float) -> str:
    """증감률. 시작이 0이면 비율이 뜻을 잃으므로 적지 않는다."""
    try:
        base = abs(float(start))
    except (TypeError, ValueError):
        return ""
    return f"({abs(change) / base * 100:.1f}%)" if base else ""


def _counted_answer(question, execution, index_truncated, available):
    """'부서가 총 몇 개야?' 처럼 지표 수를 묻는 질문."""
    found = _step_data(execution, "metric_count", "count")
    if found is None:
        return None
    listed = ", ".join(str(name) for name in found["names"][:MAX_NAMED])
    if len(found["names"]) > MAX_NAMED:
        listed += " 등"
    text = f"{found['group']}는 {listed} 모두 {found['count']}개입니다."
    return _answered(
        question, execution, index_truncated, available, text, found["references"], ()
    )


def _metric_change(execution: AgentExecution) -> dict | None:
    return _step_data(execution, "named_metric_change", "header")
