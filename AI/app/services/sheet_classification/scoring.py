from openpyxl.worksheet.worksheet import Worksheet

from app.services.formula_analyzer import FormulaAnalysis
from app.services.sheet_classification.facts import SheetFacts, sample_populated_cells
from app.services.sheet_classification.models import (
    RoleSignal,
    SheetClassification,
    SheetImportance,
    SheetRole,
    SheetRoleReason,
)


def score_classification(
    worksheet: Worksheet,
    formulas: list[FormulaAnalysis],
    facts: SheetFacts,
    signals: list[RoleSignal],
    referenced: set[str],
    referenced_by: set[str],
) -> SheetClassification:
    scores = {role: 0 for role in SheetRole if role is not SheetRole.SYSTEM}
    for signal in signals:
        scores[signal.role] += signal.weight
    fallback = _fallback_role(formulas, facts)
    if max(scores.values(), default=0) == 0:
        scores[fallback] = 1
    ranked = sorted(scores, key=lambda role: (-scores[role], role.value))
    selected = ranked[0]
    selected_score = scores[selected]
    runner_up = scores[ranked[1]] if len(ranked) > 1 else 0
    reasons = tuple(signal.reason for signal in signals if signal.role is selected)
    if not reasons:
        reasons = (
            SheetRoleReason(
                "structural_fallback",
                _fallback_message(selected),
                sample_populated_cells(worksheet),
            ),
        )
    confidence = min(
        0.98,
        round(
            0.56
            + min(0.28, max(0, selected_score - runner_up) * 0.04)
            + min(0.12, selected_score * 0.01),
            2,
        ),
    )
    score = importance_score(
        selected, worksheet, formulas, referenced, referenced_by
    )
    return SheetClassification(
        role=selected,
        importance=importance_level(score),
        confidence=confidence,
        importance_score=score,
        reasons=reasons[:4],
    )


def importance_score(
    role: SheetRole,
    worksheet: Worksheet,
    formulas: list[FormulaAnalysis],
    referenced: set[str],
    referenced_by: set[str],
) -> int:
    score = {
        SheetRole.INPUT: 30,
        SheetRole.CALCULATION: 35,
        SheetRole.OUTPUT: 45,
        SheetRole.DOCUMENTATION: 10,
        SheetRole.SYSTEM: 0,
    }[role]
    score += min(25, len(referenced_by) * 10)
    score += min(15, len(referenced) * 5)
    score += min(10, len(worksheet._charts) * 5)
    score += min(10, len(formulas) // 10 * 2)
    if worksheet.sheet_state == "visible" and role is not SheetRole.DOCUMENTATION:
        score += 5
    return min(100, score)


def importance_level(score: int) -> SheetImportance:
    if score >= 80:
        return SheetImportance.CRITICAL
    if score >= 55:
        return SheetImportance.HIGH
    if score >= 25:
        return SheetImportance.MEDIUM
    return SheetImportance.LOW


def _fallback_role(
    formulas: list[FormulaAnalysis],
    facts: SheetFacts,
) -> SheetRole:
    if formulas:
        return SheetRole.CALCULATION
    if facts.text_ratio >= 0.7 and len(facts.numeric_cells) <= 2:
        return SheetRole.DOCUMENTATION
    return SheetRole.INPUT


def _fallback_message(role: SheetRole) -> str:
    return {
        SheetRole.INPUT: "상수형 업무 데이터가 중심이어서 입력 시트로 판단",
        SheetRole.CALCULATION: "수식 구조가 중심이어서 계산 시트로 판단",
        SheetRole.OUTPUT: "표현 요소와 결과 소비 구조를 기준으로 출력 시트로 판단",
        SheetRole.DOCUMENTATION: "문장형 텍스트가 중심이어서 설명 시트로 판단",
        SheetRole.SYSTEM: "시스템 정책에 따라 시스템 시트로 판단",
    }[role]
