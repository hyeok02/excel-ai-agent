"""의도를 모델이 고르는지, 모델이 없거나 틀려도 답이 나오는지."""
import asyncio

from app.agent import create_default_tool_registry
from app.agent.query.index import IndexedCell, IndexedRow, WorkbookDataIndex
from app.agent.query.intent_models import QuestionIntent, QuestionIntentDraft
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.query_rows import selected_question_rows
from app.agent.query.service import WorkbookQuestionService
from app.services.workbook_parsing.models import WorkbookSummary

SHEET = "작업현황"
QUESTION = "여기서 챙겨봐야 할 게 뭐임?"


def _rows() -> tuple[IndexedRow, ...]:
    header = IndexedRow(SHEET, 5, (
        IndexedCell(SHEET, "C5", "장비", None),
        IndexedCell(SHEET, "D5", "네트워크 안정", None),
    ))
    body = [
        IndexedRow(SHEET, number, (
            IndexedCell(SHEET, f"C{number}", f"CVD #{number - 5}", None),
            IndexedCell(SHEET, f"D{number}", "x" if number % 2 else "o", None),
        ))
        for number in range(6, 14)
    ]
    return (header, *body)


class _Classifier:
    def __init__(self, intent: QuestionIntent | None) -> None:
        self._intent = intent

    async def classify(self, question, summary) -> QuestionIntent:
        if self._intent is None:
            raise RuntimeError("분류 실패")
        return self._intent


def test_model_intent_decides_the_rows_not_the_wording() -> None:
    # 질문의 낱말이 워크북에 하나도 없어도, 모델이 전체 질문이라 하면
    # 워크북을 대표하는 행을 읽는다.
    index = WorkbookDataIndex("tck.xlsx", _rows(), 18, False)
    summary = WorkbookSummary("tck.xlsx", 0, [])

    found = selected_question_rows(index, summary.sheets, QUESTION, 24, True)

    assert found.whole_workbook


def test_draft_from_the_model_becomes_an_intent() -> None:
    draft = QuestionIntentDraft(
        scope="whole_workbook", kind="summary", targets=[" 네트워크 안정 ", ""]
    )

    intent = QuestionIntent.from_draft(draft)

    assert intent.whole_workbook
    assert intent.targets == ("네트워크 안정",)
    assert intent.from_model


def test_model_targets_are_added_to_the_question_for_column_matching() -> None:
    intent = QuestionIntent(False, "row_list", ("네트워크 안정",), True)

    assert "네트워크 안정" in intent.enriched("불안정한 거 뭐 있어?")


def test_falls_back_to_keywords_when_the_model_cannot_be_reached() -> None:
    # 분류에 실패했다고 질문에 답하지 못할 이유는 없다.
    asyncio.run(_answered_with(_Classifier(None)))


def test_runs_without_a_classifier_at_all() -> None:
    asyncio.run(_answered_with(None))


async def _answered_with(classifier) -> None:
    service = WorkbookQuestionService(
        _Generator(), create_default_tool_registry(), classifier=classifier
    )
    answer = await service.answer(
        "네트워크 안정이 x인 장비는?",
        WorkbookSummary("tck.xlsx", 0, []),
        WorkbookDataIndex("tck.xlsx", _rows(), 18, False),
    )
    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert "CVD #2" in answer.answer


class _Generator:
    async def generate(self, *args, **kwargs):
        raise AssertionError("결정적 경로가 답해야 한다")
