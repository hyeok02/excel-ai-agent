"""A draft none of whose claims could be shown still answers an open question, on grounded numbers.

"동부가 서부보다 판매금액이 많은 이유가 뭘까?" has no cell stating a reason, so every structured
claim is dropped and nothing is shown. Here the cells and verified facts the draft cites are
shown by the server, with their own source labels, and the draft's sentences are kept as an
interpretation only when every number in them is one of those cited values. The number check
stays as strict as before; what the source does not state is shown as interpretation, not fact.
"""
import re

from app.agent.execution import AgentStepStatus
from app.agent.query.change_direction import answer_directions_supported
from app.agent.query.comparison_evidence import available_evidence, matched_comparison_evidence, present_comparison_evidence
from app.agent.query.grounded_basis import (CELL, MAX_BASIS, change_within_one_series, column_header, names, number,
                                             period_numbers, row_label, shown, source_cells)
from app.agent.query.models import (QuestionAnswer, QuestionAnswerEvidence, QuestionAnswerStatus,
                                    QuestionAnswerVerification)
from app.agent.query.numeric_support import supported_answer_numbers
from app.agent.query.references import normalize_reference
from app.agent.query.source_claims import _quotes
from app.services.insights.verification.numeric_validation import numbers, unmatched_numbers

GENERIC = "질문과 관련해 원본 Excel에서 조회한 셀"
INTERPRETED = "해석 부분은 원본에 적힌 내용이 아니라, 위 근거 수치를 바탕으로 한 추정입니다."
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


def interpreted_answer(question, draft, execution, index_truncated=False, index=None):
    steps = [step for step in execution.steps if step.status is AgentStepStatus.SUCCEEDED and step.result]
    available = available_evidence(execution)
    data = [step.result.data for step in steps if isinstance(step.result.data, dict)]
    matrix = {key: value for item in data for key, value in (item.get("source_matrix_bindings") or {}).items()}
    headers = {key: value for item in data for key, value in (item.get("source_header_bindings") or {}).items()}
    lines, evidence, values, direct, grounded = [], {}, [], [], set(numbers(question))
    for claim in draft.claims:
        if claim.kind != "verified_fact" or not isinstance(claim.fact, str):
            continue
        for fact in (fact for item in data for fact in item.get("verified_insights") or [] if isinstance(fact, dict)):
            references = fact.get("support_references", fact.get("required_references", []))
            # The fact was computed from the source by the report itself; in a large workbook the
            # search may hold only part of its cells, which are then the ones cited.
            if not _quotes(claim.fact, fact.get("fact")) or not isinstance(references, list):
                continue
            found = matched_comparison_evidence(references, available)[0] or source_cells(references, index)
            if found or index_truncated:  # a workbook too large to search whole: the fact stands uncited
                lines.append((" ".join(claim.fact.split()), None))
                grounded |= numbers(claim.fact)
                evidence.update({(item.sheet_name, item.reference): item for item in found})
                values.extend(found)
                break
    claims = {normalize_reference(claim.value_reference): claim for claim in draft.claims
              if claim.kind == "cell_value" and claim.value_reference}
    cells = [cell for reference in claims or draft.evidence
             if (cell := available.get(normalize_reference(reference))) is not None and cell.value not in (None, "")
             and CELL.fullmatch(cell.reference.replace("$", "")) and (claims or number(cell.value))]
    naming = {id(label) for cell in cells if (label := row_label(cell, available)) is not None}
    for cell in cells:
        key = normalize_reference(f"{cell.sheet_name}!{cell.reference}")
        if id(cell) in naming:
            continue  # the period or name of another cited value is shown with that value
        bound = matrix.get(key) if isinstance(matrix.get(key), dict) else None
        labels = ([available.get(bound.get("row_reference")), available.get(bound.get("column_reference"))] if bound
                  else [row_label(cell, available), column_header(cell, claims.get(key), headers.get(key), available)])
        header = cell.description.split(" (Excel 표시 형식:", 1)[0].strip()
        labels = [item for item in labels if item is not None and names(item.value)]
        if not number(cell.value) and not bound and (len(labels) < 2 or cell in labels):
            continue  # a text cell under no header is a label or header itself, not a recorded value
        parts = [shown(item) for item in labels]
        if not bound and len(labels) < 2 and header and header != GENERIC and header not in parts:
            parts.append(header)  # no header cell was read: the tool's own name for the column
        value_text = shown(cell)
        lines.append((f"{cell.sheet_name} — {' · '.join(parts) or cell.reference}: {value_text}",
                      numbers(value_text) | numbers(str(cell.value))))
        grounded |= lines[-1][1] | {found for label in labels for found in numbers(shown(label)) | period_numbers(label)}
        evidence.update({(item.sheet_name, item.reference): item for item in (cell, *labels)})
        values.append(cell)
        direct.append(cell)
    cited = list(evidence.values())
    # A difference or rate is grounded when the sentence states the two cited values it comes from;
    # a stated rise or fall is checked against those values, never against the years naming them.
    kept = [sentence.strip() for sentence in _SENTENCE.split(draft.answer) if sentence.strip()
            and not unmatched_numbers(sentence, grounded | supported_answer_numbers(question, cited, execution, sentence))
            and answer_directions_supported(sentence, values) and change_within_one_series(sentence, direct, available)]
    # A cited figure no kept sentence states is not the basis of what is shown; a quoted fact is.
    stated = numbers(" ".join(kept))
    lines = [line for line, own in dict(lines).items() if not own or own & stated][:MAX_BASIS]
    if not lines or not kept:
        return None
    limitations = [INTERPRETED] + (["대용량 워크북의 일부 셀은 검색 범위에서 제외되었습니다."] if index_truncated else [])
    return QuestionAnswer(
        question=question, answer="근거(원본 확인):\n" + "\n".join(f"· {line}" for line in lines)
        + "\n\n해석: " + " ".join(kept),
        status=QuestionAnswerStatus.LIMITED, confidence=min(draft.confidence, 0.6),
        selected_tools=[step.tool_name for step in execution.steps],
        evidence=[item if isinstance(item, QuestionAnswerEvidence) else present_comparison_evidence(item)
                  for item in evidence.values()], limitations=limitations,
        verification=QuestionAnswerVerification(
            level="source_checked", checks=["cited_cells", "source_values", "numbers", "interpretation_unverified"]))
