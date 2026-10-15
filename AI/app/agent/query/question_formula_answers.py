"""Concrete formula availability and refresh guidance with original evidence."""
import re
from dataclasses import asdict

from app.agent.query.excel_number_formats import display_value, parse_number_format
from app.agent.query.models import QuestionAnswer, QuestionAnswerEvidence, QuestionAnswerVerification
from app.agent.query.question_formula_scope import explicit_formula_refs, relevant_missing_formulas


def direct_formula_answer(question, sources, intent=None):
    if intent and intent.kind not in {"cell_lookup", "other"}:
        return None
    if re.search(r"비교|증감|합계|평균|총합|그리고|compare|sum|average|difference|\band\b|(?:값|\d)\s*(?:과|와|및)", question, re.I):
        return None
    references = explicit_formula_refs(question, sources)
    if len(references) != 1:
        return None
    requested = {value.upper().replace("$", "") for value in
                 re.findall(r"(?<![A-Za-z0-9_])\$?[A-Za-z]{1,3}\$?[1-9]\d*(?![A-Za-z0-9_])", question)}
    if len(requested) != 1 or re.search(r"[A-Za-z]\$?\d+\s*:\s*\$?[A-Za-z]", question):
        return None
    result = sources.resolutions[references[0]]
    if result.status == "unavailable":
        return _unavailable(question, [result], sources)
    if result.status != "recovered":
        return None
    cell = next(cell for row in sources.original_index.rows for cell in row.cells
                if cell.reference == result.reference)
    value = (display_value(result.value, parse_number_format(cell.number_format))
             if isinstance(result.value, (int, float)) and not isinstance(result.value, bool)
             else str(result.value))
    return QuestionAnswer(
        question=question, answer=f"{result.reference}의 재계산 값은 {value}입니다.",
        status="limited", confidence=0.85, selected_tools=["recover_formula_values"],
        evidence=[_evidence(result, sources)], limitations=[],
        verification=QuestionAnswerVerification(level="source_checked", checks=["bounded_recalculation"]),
    )


def missing_formula_answer(question, sources, intent=None):
    results = relevant_missing_formulas(question, sources, intent)
    return _unavailable(question, results, sources) if results else None


def _unavailable(question, results, sources):
    results = list({item.reference: item for item in results}.values())
    lines = ["요청과 관련된 수식에 저장된 계산 결과가 없고, 현재 파일의 입력만으로는 안전하게 복원할 수 없습니다."]
    lines.extend(f"- {item.reference}: {item.message}" for item in results[:6])
    if len(results) > 6:
        lines.append(f"그 밖에 같은 요청 범위의 수식 {len(results) - 6}개도 계산할 수 없습니다.")
    lines.append("누락된 값을 0이나 다른 셀의 값으로 대신하지 않았습니다.")
    return QuestionAnswer(
        question=question, answer="\n".join(lines), status="insufficient_evidence", confidence=0,
        selected_tools=["inspect_missing_formula_inputs"],
        evidence=[_evidence(item, sources) for item in results[:12]],
        limitations=["값이 없는 외부 데이터는 원본 연결의 갱신 또는 실제 입력 데이터가 필요합니다."
                     if any(item.reason == "external_data" for item in results)
                     else "지원하지 않는 수식이나 누락된 입력은 Excel에서 계산·저장한 결과가 필요합니다."],
    )


def _evidence(result, sources):
    cell = next(cell for row in sources.original_index.rows for cell in row.cells
                if cell.reference == result.reference)
    return QuestionAnswerEvidence(
        **{key: value for key, value in asdict(cell.evidence()).items() if key not in {"description", "value"}},
        label="재계산 수식" if result.status == "recovered" else "계산 결과가 없는 원본 수식",
        description="지원 범위 안에서 다시 계산한 수식입니다." if result.status == "recovered" else result.message,
        value=result.value if result.status == "recovered" else None,
    )
