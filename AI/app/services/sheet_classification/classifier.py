from openpyxl.worksheet.worksheet import Worksheet

from app.services.analysis_inclusion import AnalysisInclusion
from app.services.formula_analyzer import FormulaAnalysis
from app.services.sheet_classification.content_signals import content_signals
from app.services.sheet_classification.facts import extract_facts, sample_populated_cells
from app.services.sheet_classification.keywords import SYSTEM_REASON_CODES
from app.services.sheet_classification.models import (
    SheetClassification,
    SheetImportance,
    SheetRole,
    SheetRoleReason,
)
from app.services.sheet_classification.scoring import score_classification
from app.services.sheet_classification.structural_signals import structural_signals


def classify_sheet(
    worksheet: Worksheet,
    formulas: list[FormulaAnalysis],
    inclusion: AnalysisInclusion,
    referenced_sheets: set[str],
    referenced_by_sheets: set[str],
) -> SheetClassification:
    if inclusion.reason_code in SYSTEM_REASON_CODES:
        return SheetClassification(
            role=SheetRole.SYSTEM,
            importance=SheetImportance.LOW,
            confidence=0.99,
            importance_score=0,
            reasons=(
                SheetRoleReason(
                    "system_policy",
                    inclusion.reason,
                    sample_populated_cells(worksheet),
                ),
            ),
        )
    facts = extract_facts(worksheet, formulas)
    signals = structural_signals(
        worksheet,
        formulas,
        facts,
        referenced_sheets,
        referenced_by_sheets,
    )
    signals.extend(content_signals(worksheet, formulas, facts))
    return score_classification(
        worksheet,
        formulas,
        facts,
        signals,
        referenced_sheets,
        referenced_by_sheets,
    )
