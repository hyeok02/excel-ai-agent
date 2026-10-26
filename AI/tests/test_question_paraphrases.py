"""같은 뜻을 다르게 물어도 같은 답이 나오는지.

의도 판별을 낱말 목록으로 하던 때, 목록에 없는 표현은 전부 "근거 부족"이
됐다. 표현을 하나씩 목록에 더하는 식으로는 끝나지 않으므로, 한 의도당 여러
표현을 함께 묶어 둔다. 모델 분류기 없이(낱말 폴백만으로) 돌린다.
"""
import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.index import IndexedCell, IndexedRow, WorkbookDataIndex
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.query_rows import selected_question_rows
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.workbook_summary_rows import is_workbook_summary_question
from tests.tabular_query_fixtures import table_fixture

SHEET = "작업현황"
WHOLE_FILE = (
    "이 파일은 뭐에 관련된 얘기야?",
    "이 파일 뭐야?",
    "무슨 자료야?",
    "이 엑셀 어떤 내용이야?",
    "여기서 챙겨봐야 할 게 뭐임?",
    "결론만 말해줘",
)
ROW_LIST = (
    "네트워크 안정이 x인 장비는?",
    "네트워크가 불안정한 장비 알려줘",
    "네트워크 안정이 안 된 장비 뭐야?",
)
ROW_COUNT = ("장비가 총 몇 대야?", "장비 몇 개 있어?", "장비 개수 알려줘")
CELL_LOOKUP = (
    "CVD #2 IP가 뭐야?",
    "CVD #2의 IP 알려줘",
    "CVD #2 IP 좀 알려줘",
)


def _rows() -> tuple[IndexedRow, ...]:
    header = IndexedRow(SHEET, 5, (
        IndexedCell(SHEET, "C5", "IP", None),
        IndexedCell(SHEET, "D5", "장비", None),
        IndexedCell(SHEET, "E5", "네트워크 안정", None),
    ))
    body = [
        IndexedRow(SHEET, number, (
            IndexedCell(SHEET, f"C{number}", f"10.1.7.{number}", None),
            IndexedCell(SHEET, f"D{number}", f"CVD #{number - 5}", None),
            IndexedCell(SHEET, f"E{number}", "x" if number % 2 else "o", None),
        ))
        for number in range(6, 14)
    ]
    return (header, *body)


def _answer(question: str):
    service = WorkbookQuestionService(_Generator(), create_default_tool_registry())
    summary, index = table_fixture([(5, 3, [[cell.value for cell in row.cells] for row in _rows()])],
                                   sheet_name=SHEET)
    return asyncio.run(
        service.answer(question, summary, index)
    )


@pytest.mark.parametrize("question", ROW_LIST)
def test_every_wording_of_a_list_question_is_answered(question: str) -> None:
    assert "CVD #2" in _answered(question)


@pytest.mark.parametrize("question", ROW_COUNT)
def test_every_wording_of_a_count_question_is_answered(question: str) -> None:
    assert "8건" in _answered(question)


@pytest.mark.parametrize("question", CELL_LOOKUP)
def test_every_wording_of_a_lookup_question_is_answered(question: str) -> None:
    assert "10.1.7.7" in _answered(question)


@pytest.mark.parametrize("question", WHOLE_FILE)
def test_every_wording_of_a_whole_file_question_reads_the_whole_workbook(
    question: str,
) -> None:
    # 표현이 어떻든 워크북을 대표하는 행을 읽어야 한다. 질문의 낱말이 표에
    # 없다고 아무 행이나 스무 개 넘기면 모델은 답할 재료가 없다.
    index = WorkbookDataIndex("tck.xlsx", _rows(), 24, False)

    found = selected_question_rows(
        index, [], question, 24, is_workbook_summary_question(question)
    )

    assert found.whole_workbook, question


def _answered(question: str) -> str:
    answer = _answer(question)
    assert answer.status is QuestionAnswerStatus.ANSWERED, question
    return answer.answer


class _Generator:
    async def generate(self, *args, **kwargs):
        raise _ModelNeeded


class _ModelNeeded(Exception):
    pass
