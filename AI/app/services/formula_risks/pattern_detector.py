from collections import Counter, defaultdict

from openpyxl.formula.translate import Translator
from openpyxl.utils.cell import coordinate_to_tuple

from app.services.formula_analyzer import FormulaAnalysis
from app.services.formula_risks.finding_factory import build_formula_finding
from app.services.formula_risks.models import FormulaRiskFinding

MIN_RUN_LENGTH = 4
MIN_DOMINANT_RATIO = 0.75
NORMALIZATION_TARGET = "ZZ1000"


def detect_pattern_mismatches(
    formulas_by_sheet: list[tuple[str, list[FormulaAnalysis]]],
) -> list[FormulaRiskFinding]:
    findings: list[FormulaRiskFinding] = []
    reported: set[tuple[str, str]] = set()
    for sheet_name, formulas in formulas_by_sheet:
        for run in _formula_runs(formulas):
            signatures = [_signature(item) for item in run]
            counts = Counter(signatures)
            dominant, dominant_count = counts.most_common(1)[0]
            if dominant_count < 3 or dominant_count / len(run) < MIN_DOMINANT_RATIO:
                continue
            for item, signature in zip(run, signatures, strict=True):
                key = (sheet_name, item.cell)
                if signature == dominant or key in reported:
                    continue
                reported.add(key)
                findings.append(
                    build_formula_finding(
                        "formula_pattern_mismatch",
                        "warning",
                        sheet_name,
                        item,
                        "주변 셀과 다른 수식 패턴이 사용되어 복사 또는 수정 오류인지 확인이 필요합니다.",
                    )
                )
    return findings


def _formula_runs(formulas: list[FormulaAnalysis]) -> list[list[FormulaAnalysis]]:
    vertical: dict[int, list[tuple[int, FormulaAnalysis]]] = defaultdict(list)
    horizontal: dict[int, list[tuple[int, FormulaAnalysis]]] = defaultdict(list)
    for item in formulas:
        row, column = coordinate_to_tuple(item.cell)
        vertical[column].append((row, item))
        horizontal[row].append((column, item))
    runs: list[list[FormulaAnalysis]] = []
    for groups in (vertical, horizontal):
        for items in groups.values():
            runs.extend(_contiguous_runs(sorted(items, key=lambda pair: pair[0])))
    return runs


def _contiguous_runs(
    items: list[tuple[int, FormulaAnalysis]],
) -> list[list[FormulaAnalysis]]:
    runs: list[list[FormulaAnalysis]] = []
    current: list[FormulaAnalysis] = []
    previous: int | None = None
    for position, item in items:
        if previous is not None and position != previous + 1:
            if len(current) >= MIN_RUN_LENGTH:
                runs.append(current)
            current = []
        current.append(item)
        previous = position
    if len(current) >= MIN_RUN_LENGTH:
        runs.append(current)
    return runs


def _signature(item: FormulaAnalysis) -> str:
    try:
        return Translator(item.formula, origin=item.cell).translate_formula(
            NORMALIZATION_TARGET
        )
    except (TypeError, ValueError):
        return item.formula.upper()
