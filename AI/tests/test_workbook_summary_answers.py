import asyncio
from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.workbook_summary_answers import (
    validated_workbook_summary_answer,
)
from app.agent.query.workbook_summary_rows import is_workbook_summary_question
from app.services.provenance import EvidenceKind
from app.services.workbook_parsing.models import WorkbookSummary

QUESTION = "이 파일은 무엇을 비교하고 있어?"
OVERVIEW = "전체 직원 수와 부서별 직원 수의 기간별 변화를 비교합니다."


def test_service_skips_model_for_verified_workbook_summary() -> None:
    service = WorkbookQuestionService(
        _FailingGenerator(), SimpleNamespace(), _StubExecutor(_execution())
    )

    answer = asyncio.run(
        service.answer(
            QUESTION,
            WorkbookSummary("headcount.xlsx", 0, []),
            WorkbookDataIndex("headcount.xlsx", (), 0, False),
        )
    )

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.answer == OVERVIEW
    assert {item.reference for item in answer.evidence} == {"A1", "B2"}


def test_verified_summary_requires_every_support_reference() -> None:
    execution = _execution()
    execution.steps[0].result.evidence.pop()

    assert validated_workbook_summary_answer(QUESTION, execution, False) is None


def test_verified_summary_keeps_answer_when_scope_is_truncated() -> None:
    answer = validated_workbook_summary_answer(QUESTION, _execution(), True)

    assert answer is not None
    assert answer.status is QuestionAnswerStatus.LIMITED
    assert answer.answer == OVERVIEW
    assert "일부 관련 셀" in answer.limitations[0]


def _execution():
    evidence = [
        AgentExecutionEvidence(
            kind=EvidenceKind.CELL,
            sheet_name="Metrics",
            reference=reference,
            description="검증된 요약 근거",
            value=value,
        )
        for reference, value in (("A1", "Total Employees"), ("B2", 5417))
    ]
    data = {
        "workbook_summary_query": True,
        "verified_overview": OVERVIEW,
        "verified_insights": [
            {"support_references": ["Metrics!A1", "Metrics!B2"]}
        ],
        "index_truncated": False,
    }
    result = SimpleNamespace(evidence=evidence, data=data)
    step = SimpleNamespace(
        status=AgentStepStatus.SUCCEEDED,
        result=result,
        tool_name="search_workbook_data",
    )
    return SimpleNamespace(steps=[step])


class _FailingGenerator:
    async def generate(self, *_args, **_kwargs):
        raise AssertionError("검증된 요약 답변은 LLM을 호출하면 안 됩니다.")


class _StubExecutor:
    def __init__(self, execution) -> None:
        self.execution = execution

    def execute(self, *_args, **_kwargs):
        return self.execution


def test_reads_a_whole_file_question_however_it_is_worded() -> None:
    # 정해 둔 표현 목록만 보면 같은 질문도 조금만 달리 쓰면 빗나간다.
    assert is_workbook_summary_question("이 파일은 뭐에 관련된 얘기야?")
    assert is_workbook_summary_question("이 파일 뭐야?")
    assert is_workbook_summary_question("무슨 자료야?")
    assert is_workbook_summary_question("이 엑셀 어떤 내용이야?")
    assert is_workbook_summary_question("이 파일은 무엇을 다루고 있어?")
    assert is_workbook_summary_question("Summarize this file")
    assert is_workbook_summary_question("Summarize this workbook")
    assert is_workbook_summary_question("What does this file contain?")


def test_does_not_read_a_question_about_one_thing_as_a_whole_file_question() -> None:
    # 파일을 가리키는 말이 있어도 다른 대상이 남으면 전체 질문이 아니다.
    assert not is_workbook_summary_question("이 파일 어떤 장비가 문제야?")
    assert not is_workbook_summary_question("이 파일은 어떤 시트로 구성돼 있어?")
    assert not is_workbook_summary_question("장비가 총 몇 대야?")
    assert not is_workbook_summary_question("네트워크 안정의 표시별 건수를 요약해줘")
    assert is_workbook_summary_question("이 파일을 요약해줘")


def test_a_brief_answer_keeps_what_the_file_is_and_one_fact() -> None:
    from app.agent.query.workbook_summary_answers import _shortened

    overview = (
        "이 파일은 CVD 장비 17건을 점검한 표입니다. "
        "12건이 점검됐고 5건은 비어 있습니다. "
        "‘네트워크 안정’이 x인 건이 7건으로 가장 많습니다."
    )

    assert _shortened(overview) == (
        "이 파일은 CVD 장비 17건을 점검한 표입니다. 12건이 점검됐고 5건은 비어 있습니다."
    )


def test_a_short_overview_is_left_alone() -> None:
    from app.agent.query.workbook_summary_answers import _shortened

    overview = "이 파일은 CVD 장비 17건을 점검한 표입니다."

    assert _shortened(overview) == overview
