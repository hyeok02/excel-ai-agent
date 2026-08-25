from openpyxl.worksheet.worksheet import Worksheet

from app.services.regions.models import RegionBounds
from app.services.regions.role_rules import (
    CALCULATION_PATTERN,
    INPUT_PATTERN,
    INSTRUCTION_PATTERN,
    NOTE_PATTERN,
    OUTPUT_PATTERN,
    ROLE_CONFIDENCE,
    ROLE_REASONS,
    RULE_PATTERN,
    SOURCE_PATTERN,
    TITLE_KEYWORDS,
    TOTAL_PATTERN,
    UNIT_PATTERN,
    WARNING_PATTERN,
)
from app.services.regions.utils import (
    evidence_cells,
    formula_count,
    intersecting_merged_ranges,
    region_text,
    region_values,
    row_data_count,
    style_emphasis_count,
    sub_bounds,
)
from app.services.semantic_models import SemanticClassification, SemanticReason, SemanticRole


def explicit_role(
    worksheet: Worksheet,
    bounds: RegionBounds,
    sheet_role: str | None,
) -> SemanticRole | None:
    text = region_text(worksheet, bounds)
    formulas = formula_count(worksheet, bounds)
    if sheet_role == "system":
        return SemanticRole.SYSTEM_CACHE
    if sheet_role == "documentation":
        return SemanticRole.INSTRUCTION
    for pattern, role in (
        (WARNING_PATTERN, SemanticRole.WARNING),
        (SOURCE_PATTERN, SemanticRole.SOURCE_NOTE),
        (NOTE_PATTERN, SemanticRole.NOTE),
        (INPUT_PATTERN, SemanticRole.INPUT),
        (CALCULATION_PATTERN, SemanticRole.CALCULATION),
    ):
        if pattern.search(text):
            return role
    if OUTPUT_PATTERN.search(text) and formulas:
        return SemanticRole.OUTPUT
    if RULE_PATTERN.search(text) and formulas == 0:
        return SemanticRole.RULE_NOTE
    return None


def fallback_role(
    worksheet: Worksheet,
    bounds: RegionBounds,
    sheet_role: str | None,
) -> SemanticRole:
    text = region_text(worksheet, bounds)
    values = region_values(worksheet, bounds)
    formulas = formula_count(worksheet, bounds)
    merged = intersecting_merged_ranges(worksheet, bounds)
    emphasized = style_emphasis_count(worksheet, bounds)
    if UNIT_PATTERN.search(text):
        return SemanticRole.UNIT
    if INSTRUCTION_PATTERN.search(text):
        return SemanticRole.INSTRUCTION
    if _is_title(bounds, values, merged, emphasized, text):
        return SemanticRole.TITLE
    if formulas:
        return SemanticRole.CALCULATION
    if values and all(isinstance(value, str) for value in values):
        return SemanticRole.DESCRIPTION
    if sheet_role == "input":
        return SemanticRole.INPUT
    if sheet_role == "output":
        return SemanticRole.OUTPUT
    return SemanticRole.DATA


def classify(
    worksheet: Worksheet,
    bounds: RegionBounds,
    role: SemanticRole,
    confidence: float | None = None,
    extra_reasons: tuple[SemanticReason, ...] = (),
) -> SemanticClassification:
    reason_code, message = ROLE_REASONS.get(
        role,
        ("semantic_fallback", "셀 값과 서식 분포를 기준으로 역할을 판단"),
    )
    return SemanticClassification(
        role=role,
        confidence=confidence or ROLE_CONFIDENCE.get(role, 0.72),
        reasons=(
            SemanticReason(
                code=reason_code,
                message=message,
                evidence_cells=evidence_cells(worksheet, bounds),
            ),
            *extra_reasons,
            *bounds.boundary_reasons,
        ),
    )


def is_total_row(worksheet: Worksheet, bounds: RegionBounds, row: int) -> bool:
    values = region_values(worksheet, sub_bounds(bounds, row, row))
    has_label = any(
        isinstance(value, str) and TOTAL_PATTERN.fullmatch(value.strip())
        for value in values
    )
    return has_label and row_data_count(worksheet, bounds, row) > 0


def _is_title(
    bounds: RegionBounds,
    values: list[object],
    merged: list[str],
    emphasized: int,
    text: str,
) -> bool:
    return bool(
        bounds.min_row <= 2
        and len(values) <= 2
        and merged
        and emphasized
        and (
            bounds.min_row == 1
            or any(keyword in text.lower() for keyword in TITLE_KEYWORDS)
        )
    )
