from openpyxl import Workbook

from app.services.formula_analyzer import FormulaAnalysis
from app.services.formula_risks import detect_formula_risks


def _formula(cell: str, formula: str, references: list[str]) -> FormulaAnalysis:
    return FormulaAnalysis(cell=cell, formula=formula, references=references)


def test_detects_formula_pattern_mismatch_in_repeated_column() -> None:
    formulas = [
        _formula("B2", "=A2*2", ["A2"]),
        _formula("B3", "=A3*2", ["A3"]),
        _formula("B4", "=A4+99", ["A4"]),
        _formula("B5", "=A5*2", ["A5"]),
    ]

    summary = detect_formula_risks(["Calc"], [("Calc", formulas)])

    assert summary.pattern_mismatch_count == 1
    assert summary.findings[0].cell == "B4"
    assert summary.findings[0].kind == "formula_pattern_mismatch"


def test_detects_numeric_value_between_matching_formulas() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Calc"
    worksheet["B3"] = "=A3*2"
    worksheet["B4"] = 999
    worksheet["B5"] = "=A5*2"
    formulas = [
        _formula("B3", "=A3*2", ["A3"]),
        _formula("B5", "=A5*2", ["A5"]),
    ]

    summary = detect_formula_risks(
        ["Calc"],
        [("Calc", formulas)],
        [worksheet],
    )

    assert summary.hardcoded_value_count == 1
    finding = summary.findings[0]
    assert finding.cell == "B4"
    assert finding.observed_value == 999
    assert finding.formula == "=A4*2"
    workbook.close()
