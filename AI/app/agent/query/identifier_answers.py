"""Give a clear answer when an explicit workbook row identifier is absent."""

import re

from app.agent.query.index import WorkbookDataIndex
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus

HASH_IDENTIFIER = re.compile(
    r"(?:(?P<prefix>[0-9a-z가-힣][0-9a-z가-힣_-]*)\s*)?"
    r"#\s*(?P<identifier>[0-9a-z][0-9a-z_-]*)",
    re.I,
)


def missing_identifier_answer(
    question: str, index: WorkbookDataIndex
) -> QuestionAnswer | None:
    if index.truncated:
        return None
    requested = _identifiers(question)
    if not requested:
        return None
    present = {
        item
        for row in index.rows
        for cell in row.cells
        if isinstance(cell.value, str)
        for item in _identifiers(cell.value)
    }
    missing = [
        item for item in requested
        if item[0] and any(found[0] == item[0] for found in present)
        and item not in present
    ]
    if not missing:
        return None
    labels = ", ".join(f"#{value}" for _, value in missing)
    return QuestionAnswer(
        question=question,
        answer=f"원본 워크북에서 {labels} 항목을 찾지 못했습니다.",
        status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE,
        confidence=0,
        selected_tools=[],
        evidence=[],
        limitations=["질문에 적힌 식별자와 일치하는 셀이 없습니다."],
    )


def _identifiers(text: str) -> list[tuple[str, str]]:
    return list(dict.fromkeys(
        (
            (match.group("prefix") or "").casefold(),
            match.group("identifier").casefold(),
        )
        for match in HASH_IDENTIFIER.finditer(text)
    ))
