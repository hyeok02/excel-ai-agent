"""Keep derived formula results visibly distinct from saved original values."""
from dataclasses import asdict
from openpyxl.utils import range_boundaries

from app.agent.query.models import QuestionAnswerEvidence, QuestionAnswerVerification
from app.services.provenance import EvidenceKind


def finish_formula_answer(answer, sources):
    if answer.status == "insufficient_evidence":
        return answer
    used = [item for item in sources.resolutions.values() if item.status == "recovered"
            and any(_covers(evidence, item.reference) for evidence in answer.evidence)]
    if not used:
        return answer
    original = {cell.reference: cell for row in sources.original_index.rows for cell in row.cells}
    recovered = {item.reference: item for item in used}
    evidence = []
    for item in answer.evidence:
        if any(_covers(item, reference) for reference in recovered):
            item = item.model_copy(update={
                "label": item.label + " · 재계산 포함",
                "description": "원본 입력과 지원 범위 내 수식 재계산 결과를 함께 사용한 근거입니다. 재계산 값은 파일에 저장된 원본 계산 결과가 아닙니다.",
            })
        evidence.append(item)
    existing = {(item.sheet_name, item.reference) for item in evidence}
    references = list(dict.fromkeys([item.reference for item in used] + [ref for item in used for ref in item.inputs]))
    for reference in references[:80]:
        cell = original.get(reference)
        sheet, _, address = reference.rpartition("!")
        if (sheet, address) in existing:
            continue
        if cell is None:
            evidence.append(QuestionAnswerEvidence(
                kind=EvidenceKind.CELL, sheet_name=sheet, reference=address,
                label="재계산 입력 원본 · 빈 셀", value=None,
                description="잘리지 않은 원본 시트에서 내용이 없는 셀로 확인한 수식 입력입니다.",
            ))
            existing.add((sheet, address))
            continue
        resolution = sources.resolutions.get(reference)
        derived = resolution is not None and resolution.status == "recovered"
        evidence.append(QuestionAnswerEvidence(
            **{key: value for key, value in asdict(cell.evidence()).items() if key not in {"description", "value"}},
            label="재계산 수식" if derived else "재계산 입력 원본",
            description=("원본에 저장된 계산 결과가 없어 입력 셀로 다시 계산한 값입니다."
                         if derived else "수식 재계산에 사용한 원본 입력 셀입니다."),
            value=resolution.value if derived else cell.value,
        ))
        existing.add((sheet, address))
    note = (f"원본에 저장된 결과가 없는 수식 {len(used)}개를 워크북 내부 입력으로 재계산했습니다. "
            "Excel·외부 서비스에서 갱신된 최신 값임을 확인한 것은 아닙니다.")
    if len(references) > 80:
        note += " 재계산 입력 근거는 앞의 80개 참조까지만 표시했습니다."
    return answer.model_copy(update={
        "status": "limited", "confidence": min(answer.confidence, 0.85),
        "evidence": evidence, "limitations": list(dict.fromkeys([*answer.limitations, note])),
        "selected_tools": list(dict.fromkeys([*answer.selected_tools, "recover_formula_values"])),
        "verification": QuestionAnswerVerification(level="source_checked", checks=[
            "formula_inputs", "bounded_recalculation",
            *[check for check in answer.verification.checks
              if check not in {"source_values", "source_cells", "request_alignment"}],
        ]),
    })


def _covers(evidence, reference):
    sheet, _, address = reference.rpartition("!")
    if evidence.sheet_name != sheet or not evidence.reference:
        return False
    try:
        left, top, right, bottom = range_boundaries(evidence.reference.replace("$", ""))
        column, row, _, _ = range_boundaries(address)
        return left <= column <= right and top <= row <= bottom
    except (ValueError, TypeError):
        return False
