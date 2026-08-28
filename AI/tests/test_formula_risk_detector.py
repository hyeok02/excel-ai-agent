from app.services.formula_analyzer import FormulaAnalysis
from app.services.formula_risks import detect_formula_risks


def _formula(cell: str, formula: str) -> FormulaAnalysis:
    return FormulaAnalysis(cell=cell, formula=formula, references=[])


def test_detects_broken_missing_external_and_dynamic_references() -> None:
    summary = detect_formula_risks(
        ["Summary", "Input Data"],
        [
            (
                "Summary",
                [
                    _formula("A1", "=#REF!+1"),
                    _formula("A2", "='Deleted Sheet'!B2"),
                    _formula("A3", "='[Budget.xlsx]Plan'!C3"),
                    _formula("A4", '=INDIRECT("A"&1)+OFFSET(B1,1,0)'),
                ],
            )
        ],
    )

    assert summary.total_count == 5
    assert summary.error_count == 2
    assert summary.warning_count == 3
    assert summary.broken_reference_count == 1
    assert summary.missing_sheet_count == 1
    assert summary.external_reference_count == 1
    assert summary.dynamic_function_count == 2
    assert {item.function_name for item in summary.findings} >= {"INDIRECT", "OFFSET"}
    assert all(item.provenance is not None for item in summary.findings)


def test_existing_quoted_sheet_is_not_reported_as_missing() -> None:
    summary = detect_formula_risks(
        ["Summary", "Input Data"],
        [("Summary", [_formula("A1", "='Input Data'!B2")])],
    )

    assert summary.total_count == 0
    assert summary.findings == []


def test_repeated_risk_in_one_formula_is_reported_once() -> None:
    summary = detect_formula_risks(
        ["Summary"],
        [("Summary", [_formula("A1", "=INDIRECT(A1)+INDIRECT(B1)")])],
    )

    assert summary.dynamic_function_count == 1


def test_long_concatenation_formula_is_not_misclassified_as_risk() -> None:
    joined_cells = "&".join(f"K{row}" for row in range(79, 381))
    formula = f'=IF(SUM($J$79:$J$380)=0,"",{joined_cells})'

    summary = detect_formula_risks(
        ["Intermediate"],
        [("Intermediate", [_formula("G8", formula)])],
    )

    assert summary.total_count == 0
