import re

from app.agent.query.models import (
    QuestionAnswer,
    QuestionAnswerDraft,
    QuestionAnswerStatus,
)

_GENERIC_INPUTS = {
    "안녕",
    "응",
    "예",
    "아니",
    "뭐",
    "질문",
    "테스트",
    "도와줘",
    "hello",
    "test",
    "ok",
    "okay",
}
_SPECIFIC_TERMS = (
    "요약 분석 알려 보여 찾아 확인 검토 비교 계산 설명 얼마 몇 무엇 무슨 왜 어떻게 "
    "어디 언제 어때 추이 증가 감소 변화 오류 위험 수식 참조 매출 비용 이익 직원 인원 "
    "부서 투자 거래 날짜 기간 합계 평균 최대 최소 값 셀 시트 파일 워크북 what which how "
    "why show find summary analy compare formula cell sheet revenue sales employee headcount investment"
).split()
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


def vague_question_answer(question: str) -> QuestionAnswer | None:
    meaningful = re.sub(r"[^0-9A-Za-z가-힣]", "", question).casefold()
    repeated = len(meaningful) < 4 and len(set(meaningful)) == 1
    has_cell = bool(re.search(r"\b[a-z]{1,3}\$?\d+\b", question, re.IGNORECASE))
    has_term = any(term in meaningful for term in _SPECIFIC_TERMS)
    if (
        meaningful
        and meaningful not in _GENERIC_INPUTS
        and not repeated
        and (has_cell or (len(meaningful) >= 3 and has_term))
    ):
        return None
    return clarification_answer(question)


def unclear_draft_answer(
    question: str, draft: QuestionAnswerDraft
) -> QuestionAnswer | None:
    text = " ".join([draft.answer, *draft.limitations])
    return clarification_answer(question) if any(item in text for item in _UNCLEAR_MARKERS) else None
