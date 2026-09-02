import re

from app.agent.query.index import WorkbookDataIndex
from app.agent.query.models import (
    QuestionAnswer,
    QuestionAnswerDraft,
    QuestionAnswerStatus,
)
from app.agent.query.search_terms import relevance, search_terms

CELL_PATTERN = re.compile(r"\b[a-z]{1,3}\$?\d+\b", re.IGNORECASE)
MIN_CONTENT_TERMS = 2

# 무엇을 묻는지를 나타내는 표현과 스프레드시트 자체의 어휘만 둔다.
# 업종 명사(매출·직원·부서 등)는 여기에 두지 않고 워크북이 직접 제공한다.
INTENT_MARKERS = (
    "요약", "분석", "알려", "보여", "찾아", "확인", "검토", "비교", "계산", "설명",
    "얼마", "몇", "무엇", "무슨", "왜", "어떻게", "어디", "언제", "어때",
    "추이", "변화", "증가", "감소", "합계", "평균", "최대", "최소",
    "오류", "위험", "수식", "참조", "시트", "워크북", "셀",
    "what", "which", "how", "why", "show", "find", "summar", "analy",
    "compare", "total", "average", "formula", "cell", "sheet", "error", "risk",
)
_UNCLEAR_MARKERS = (
    "질문이 불분명",
    "질문이 명확하지",
    "명확한 의미를 파악할 수 없",
    "질문의 의미를 파악할 수 없",
    "구체적인 분석이나 설명을 제공할 수 없",
)


def clarification_answer(question: str) -> QuestionAnswer:
    return QuestionAnswer(
        question=question.strip(),
        answer=(
            "질문이 구체적이지 않아 무엇을 확인해야 할지 모르겠습니다. "
            "확인할 항목이나 기간을 포함해 다시 질문해주세요."
        ),
        status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE,
        confidence=0,
        selected_tools=[],
        evidence=[],
        limitations=[],
    )


def vague_question_answer(
    question: str, data_index: WorkbookDataIndex | None = None
) -> QuestionAnswer | None:
    """Agent를 실행할 가치가 있는 질문인지 판단한다.

    업종별 용어집 대신 세 가지 근거로만 본다. (1) 셀 주소를 직접 가리키는지,
    (2) 무엇을 묻는지를 나타내는 표현이 있는지, (3) 질문에 쓰인 단어가 지금
    올라온 워크북 안에 실제로 있는지. 도메인 판단을 업로드된 파일에 넘기므로
    인사 파일이든 회계 파일이든 같은 규칙이 적용된다.
    """
    meaningful = re.sub(r"[^0-9A-Za-z가-힣]", "", question).casefold()
    if not meaningful or (len(meaningful) < 4 and len(set(meaningful)) == 1):
        return clarification_answer(question)
    if CELL_PATTERN.search(question) or _has_intent(meaningful):
        return None
    terms = search_terms(question)
    if len(terms) >= MIN_CONTENT_TERMS or _matches_workbook(terms, data_index):
        return None
    return clarification_answer(question)


def unclear_draft_answer(
    question: str, draft: QuestionAnswerDraft
) -> QuestionAnswer | None:
    text = " ".join([draft.answer, *draft.limitations])
    return (
        clarification_answer(question)
        if any(item in text for item in _UNCLEAR_MARKERS)
        else None
    )


def _has_intent(meaningful: str) -> bool:
    return any(marker in meaningful for marker in INTENT_MARKERS)


def _matches_workbook(
    terms: list[str], data_index: WorkbookDataIndex | None
) -> bool:
    if not terms or data_index is None:
        return False
    return any(relevance(row, terms) for row in data_index.rows)
