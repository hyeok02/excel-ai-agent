from dataclasses import replace
from datetime import date

import pytest

from app.agent.query.formula_resolution import FormulaResolver
from app.agent.query.formula_resolution_models import FormulaLimits
from tests.test_formula_resolution import workbook_index
from tests.test_formula_resolution_conditions import conditional_result
from tests.test_formula_resolution_lookups import lookup_result


def test_cross_sheet_lookup_chains_keep_all_examined_original_references():
    index = workbook_index([["=VLOOKUP(\"B\",'Other sheet'!A1:B3,2,FALSE)"]],
                           [["A", 8], ["B", "=B1*2"], ["C", "=_xll.Remote()"]])
    result = FormulaResolver(index).resolve("Data!A1")
    assert result.status == "recovered" and result.value == 16
    assert set(result.inputs) == {"Other sheet!A1", "Other sheet!A2", "Other sheet!B1", "Other sheet!B2"}


def test_typed_date_criteria_can_match_without_assuming_text_date_locale():
    result = conditional_result('=COUNTIF(A1:A2,DATE(2025,1,1))',
                                [[date(2025, 1, 1), 1, 1], [date(2025, 1, 2), 2, 1]])
    assert result.status == "recovered" and result.value == 1


@pytest.mark.parametrize("formula", [
    '=IFERROR(COUNTIF(A1:A2,"Alpha"),99)',
    '=IFERROR(SUMIF(A1:A2,"Alpha",B1:B2),99)',
    '=IFERROR(XLOOKUP("Alpha",A1:A2,B1:B2),99)',
])
def test_reference_functions_respect_truncated_sheet_guards(formula):
    index = replace(workbook_index([["Alpha", 8, formula], ["Beta", 12]]),
                    truncated=True, truncated_sheet_names=frozenset({"Data"}))
    result = FormulaResolver(index).resolve("Data!C1")
    assert result.status == "unavailable" and result.reason == "index_truncated"


@pytest.mark.parametrize("formula,limits", [
    ('=COUNTIF(A1:A3,"Alpha")', FormulaLimits(max_cells=2)),
    ('=SUMIF(A1:A3,"Alpha",B1:B3)', FormulaLimits(max_range_cells=2)),
    ('=XLOOKUP("Beta",A1:A3,B1:B3)', FormulaLimits(max_cells=2)),
    ('=INDEX(A1:C3,1,2)', FormulaLimits(max_range_cells=2)),
])
def test_reference_functions_respect_shared_cell_and_range_budgets(formula, limits):
    result = FormulaResolver(workbook_index([["Alpha", 8, None, formula], ["Beta", 12], ["Alpha", 13]]),
                             limits).resolve("Data!D1")
    assert result.status == "unavailable" and result.reason == "resource_limit"


def test_wildcard_matching_cannot_run_unbounded_regex_backtracking():
    pattern = "*a" * 100 + "b"
    result = conditional_result(f'=COUNTIF(A1:A2,"{pattern}")', [["a" * 2000, 1, 1], ["b", 1, 1]])
    assert result.status == "unavailable" and result.reason == "resource_limit"


@pytest.mark.parametrize("formula", [
    '=IFERROR(VLOOKUP("Absent",A1:B2,2,FALSE),99)',
    '=IFERROR(XLOOKUP("Absent",A1:A2,B1:B2,"none"),99)',
    '=IFERROR(MATCH("Absent",A1:A2,0),99)',
])
def test_lookup_key_errors_do_not_fabricate_no_match_or_fallback(formula):
    result = lookup_result(formula, [["Alpha", 8, 1], ["#N/A", 12, 1]])
    assert result.status == "unavailable" and result.reason == "unsupported_expression"


@pytest.mark.parametrize("formula", [
    '=IFERROR(COUNTIF(A1:A2,"ß"),99)',
    '=IFERROR(XLOOKUP("ß",A1:A2,B1:B2),99)',
])
def test_locale_dependent_case_expansions_do_not_invent_zero_or_matches(formula):
    result = lookup_result(formula, [["ß", 8, 1], ["ss", 12, 1]])
    assert result.status == "unavailable" and result.reason == "unsupported_expression"


@pytest.mark.parametrize("criterion", ['"1,000"', '" 10"'])
def test_locale_or_whitespace_numeric_coercion_is_not_guessed(criterion):
    result = conditional_result(f"=IFERROR(COUNTIF(A1:A2,{criterion}),99)", [[10, 1, 1], [1000, 1, 1]])
    assert result.status == "unavailable" and result.reason == "unsupported_expression"


@pytest.mark.parametrize("expression", [
    'VLOOKUP("A",A1:B2,2,FALSE)', 'XLOOKUP("A",A1:A2,B1:B2)',
    'COUNTA(VLOOKUP("A",A1:B2,2,FALSE))',
    '"["&XLOOKUP("A",A1:A2,B1:B2)&"]"',
    'SUM(VLOOKUP("B",A1:B2,2,FALSE))',
])
def test_context_dependent_lookup_blank_and_text_results_are_not_guessed(expression):
    result = lookup_result(f"=IFERROR({expression},99)", [["A", None, 1], ["B", "10", 1]])
    assert result.status == "unavailable" and result.reason == "unsupported_expression"


def test_negated_wildcard_blank_semantics_cannot_produce_a_wrong_count():
    result = conditional_result('=IFERROR(COUNTIF(A1:A4,"<>*"),99)',
                                [["Alpha", 1, 1], [None, 2, 1], [3, 3, 1], ['=""', 4, 1]])
    assert result.status == "unavailable" and result.reason == "unsupported_expression"
