"""Answer a question that names a verified insight by its full title with that insight.

Suggested questions repeat an insight title inside a fixed request ("{title} 관련
수치와 원본 근거를 보여줘"). When a model plan for such a question ends in a
clarification or refusal, the insight the question names is the answer: its fact
was already verified against the cited cells, which are re-read here. Anything
else in the question (a condition, period or operation) keeps the original answer.
"""
import re

from openpyxl.utils.cell import range_boundaries, get_column_letter

from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.verified_facts import build_verified_question_context

# Request wording of the suggested-question templates; it adds no condition.
_REQUEST_WORDS = frozenset({
    "관련", "수치", "수치와", "원본", "근거", "근거를", "근거와", "보여줘", "알려줘", "확인된", "위험과", "위험",
    "설명해줘", "수식과", "수식", "참조", "관계를", "구성을", "기록된", "내용을", "함께", "요약해줘",
})
_PARTICLE = re.compile(r"(?:을|를|은|는|이|가|의|에서|에|와|과)$")
MAX_CELLS = 120


def insight_title_answer(question, summary, index):
    if summary is None or index is None:
        return None
    asked = _normal(question)
    named = [item for item in build_verified_question_context(summary)["insights"]
             if len(title := _normal(item.get("title") or "")) >= 4 and title in asked]
    if not named:
        return None
    longest = max(len(_normal(item["title"])) for item in named)
    named = [item for item in named if len(_normal(item["title"])) == longest]
    if len(named) != 1 or not _only_request(asked.replace(_normal(named[0]["title"]), " ")):
        return None
    item = named[0]
    cells = _cited_cells(item.get("evidence") or (), index)
    if not cells:
        return None
    return QuestionAnswer(
        question=question, answer=str(item["fact"]), status=QuestionAnswerStatus.ANSWERED,
        confidence=min(float(item.get("confidence") or 1.0), 1.0), selected_tools=["verified_insight"],
        evidence=[_evidence(cell) for cell in cells[:MAX_CELLS]], limitations=[],
        verification=QuestionAnswerVerification(level="source_checked", checks=["cited_cells", "verified_insight_fact"]),
    )


def _only_request(rest):
    words = re.findall(r"[가-힣]+|[a-z0-9]+", rest)
    return all(word in _REQUEST_WORDS or _PARTICLE.sub("", word) in _REQUEST_WORDS | {""} for word in words)


def _cited_cells(evidence, index):
    """Every cited cell must still exist in the current file; ranges are expanded."""
    indexed = {cell.reference: cell for row in index.rows for cell in row.cells}
    found = []
    for value in evidence:
        sheet, _, area = str(value).rpartition("!")
        sheet = sheet[1:-1].replace("''", "'") if sheet.startswith("'") and sheet.endswith("'") else sheet
        try:
            left, top, right, bottom = range_boundaries(area.replace("$", ""))
        except (TypeError, ValueError):
            return []
        addresses = [f"{sheet}!{get_column_letter(column)}{row}"
                     for row in range(top, bottom + 1) for column in range(left, right + 1)]
        present = [indexed[address] for address in addresses if address in indexed]
        if left == right and top == bottom and not present:
            return []  # A single cited cell that no longer exists.
        found.extend(present)
    return list(dict.fromkeys(found))


def _normal(value):
    return re.sub(r"\s+", " ", str(value).casefold()).strip()
