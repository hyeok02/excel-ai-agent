from app.services.formula_analyzer import FormulaAnalysis
from app.services.formula_risks.finding_factory import build_hardcoded_finding
from app.services.formula_risks.impact_analyzer import add_impact_analysis


def _formula(cell: str, formula: str, references: list[str]) -> FormulaAnalysis:
    return FormulaAnalysis(cell=cell, formula=formula, references=references)


def test_calculates_transitive_formula_and_sheet_impact() -> None:
    finding = build_hardcoded_finding("Input", "A2", 100, "=A1*2")
    formulas = [
        ("Input", []),
        ("Calc", [_formula("B2", "=Input!A2*2", ["Input!A2"])]),
        ("Summary", [_formula("C2", "=Calc!B2", ["Calc!B2"])]),
    ]

    enriched = add_impact_analysis([finding], formulas)[0]

    assert enriched.impact is not None
    assert enriched.impact.affected_formula_count == 2
    assert enriched.impact.affected_sheet_count == 2
    assert enriched.impact.affected_sheets == ["Calc", "Summary"]
    assert enriched.impact.max_depth == 2
    assert enriched.impact.risk_level == "high"


def test_range_reference_is_included_in_impact() -> None:
    finding = build_hardcoded_finding("Input", "A3", 100, "=A2+1")
    formulas = [
        ("Input", []),
        ("Summary", [_formula("B1", "=SUM(Input!A1:A5)", ["Input!A1:A5"])]),
    ]

    enriched = add_impact_analysis([finding], formulas)[0]

    assert enriched.impact is not None
    assert enriched.impact.affected_formula_count == 1
    assert enriched.impact.affected_sheets == ["Summary"]
