import pytest

from app.agent.query.formula_resolution import FormulaResolver
from tests.test_formula_resolution import workbook_index


def lookup_result(formula, rows=None):
    data = rows or [["Alpha", 10, 1], ["Beta", 20, 2], ["alpha", 30, 3], ["A*", 40, 4]]
    data = [list(row) for row in data]
    data[0] = [*data[0], None, formula]
    return FormulaResolver(workbook_index(data)).resolve("Data!E1")


@pytest.mark.parametrize("formula,expected", [
    ('=INDEX(B1:B4,2)', 20), ('=INDEX(A1:C4,2,2)', 20),
    ('=INDEX(A1:C1,2)', 10), ('=INDEX(A1:C1,,2)', 10),
    ('=MATCH("BETA",A1:A4,0)', 2), ('=MATCH("A~*",A1:A4,0)', 4),
    ('=MATCH("?eta",A1:A4,0)', 2), ('=MATCH(20,B1:B4,0)', 2),
    ('=INDEX(B1:B4,MATCH("Beta",A1:A4,0))', 20),
    ('=VLOOKUP("Beta",A1:C4,2,FALSE)', 20),
    ('=VLOOKUP("A~*",A1:C4,3,0)', 4),
    ('=HLOOKUP(10,A1:C4,3,FALSE)', 30),
    ('=XLOOKUP("Beta",A1:A4,B1:B4)', 20),
    ('=_xlfn.XLOOKUP("alpha",A1:A4,B1:B4)', 10),
    ('=XLOOKUP("alpha",A1:A4,B1:B4,,0,-1)', 30),
    ('=XLOOKUP("A*",A1:A4,B1:B4)', 40),
    ('=XLOOKUP("A*",A1:A4,B1:B4,,2)', 10),
    ('=XLOOKUP("Missing",A1:A4,B1:B4,"not found")', "not found"),
    ('=IFERROR(VLOOKUP("Missing",A1:C4,2,FALSE),99)', 99),
    ('=IFERROR(XLOOKUP("Missing",A1:A4,B1:B4),99)', 99),
    ('=SUM(INDEX(B1:B4,1),XLOOKUP("Beta",A1:A4,B1:B4))', 30),
])
def test_exact_lookup_scalar_results(formula, expected):
    result = lookup_result(formula)
    assert result.status == "recovered" and result.value == expected


def test_lookup_preserves_only_examined_keys_and_selected_return_lineage():
    result = lookup_result('=XLOOKUP("Beta",A1:A4,B1:B4)')
    assert set(result.inputs) == {"Data!A1", "Data!A2", "Data!B2"}
    result = lookup_result('=XLOOKUP("alpha",A1:A4,B1:B4,,0,-1)')
    assert set(result.inputs) == {"Data!A4", "Data!A3", "Data!B3"}


@pytest.mark.parametrize("formula", [
    '=IFERROR(VLOOKUP("Alpha",A1:C4,2),0)',
    '=IFERROR(VLOOKUP("Alpha",A1:C4,2,TRUE),0)',
    '=IFERROR(MATCH("Alpha",A1:A4),0)',
    '=IFERROR(MATCH("Alpha",A1:A4,1),0)',
    '=IFERROR(XLOOKUP("Alpha",A1:A4,B1:B4,,1),0)',
    '=IFERROR(XLOOKUP("Alpha",A1:A4,B1:B4,,0,2),0)',
    '=IFERROR(XLOOKUP("Alpha",A1:A4,B1:C4),0)',
    '=IFERROR(INDEX(A1:C4,0,2),0)',
    '=INDEX(A1:C4,,2)',
    '=IFERROR(SUM(INDEX(A1:C4,,2)),0)',
    '=IFERROR(INDEX(A1:C4,2,),0)',
    '=IFERROR(INDEX(A1:A4,),0)',
    '=IFERROR(INDEX(A1:C1,,),0)',
    '=IFERROR(INDEX(A1:C4,2),0)',
    '=IFERROR(INDEX(B1:B4,1.5),0)',
])
def test_approximate_and_array_modes_are_not_inferred_or_iferror_masked(formula):
    result = lookup_result(formula)
    assert result.status == "unavailable" and result.reason == "unsupported_expression"


@pytest.mark.parametrize("formula", [
    '=IFERROR(XLOOKUP("Alpha",A1:A2,B1:B2,99),0)',
    '=IFERROR(VLOOKUP("Alpha",A1:B2,2,FALSE),0)',
    '=IFERROR(INDEX(B1:B2,MATCH("Alpha",A1:A2,0)),0)',
])
def test_missing_selected_external_result_is_never_iferror_fallback(formula):
    result = lookup_result(formula, [["Alpha", "=_xll.Remote()", 1], ["Beta", 20, 2]])
    assert result.status == "unavailable" and result.reason == "external_data"


def test_unselected_external_values_do_not_block_known_lookup():
    result = lookup_result('=XLOOKUP("Alpha",A1:A2,B1:B2,_xll.Remote())',
                           [["Alpha", 10, 1], ["Beta", "=_xll.Remote()", 2]])
    assert result.status == "recovered" and result.value == 10


def test_lookup_numeric_text_is_not_coerced_into_numeric_identifier():
    result = lookup_result('=XLOOKUP(10,A1:A2,B1:B2)', [["10", 9, 1], [10, 12, 2]])
    assert result.value == 12


@pytest.mark.parametrize("formula", [
    '=IFERROR(XLOOKUP(A1:A2,A1:A2,B1:B2),99)',
    '=IFERROR(XLOOKUP("Missing",A1:A2,B1:B2,B1:B2),99)',
    '=IFERROR(MATCH(A1:A2,A1:A2,0),99)',
    '=IFERROR(SUM(INDEX(A1:A2,1)),99)',
    '=IFERROR(COUNT(XLOOKUP("10",A1:A2,A1:A2)),99)',
])
def test_array_errors_and_reference_text_are_not_wrongly_recovered_as_scalar(formula):
    result = lookup_result(formula, [["10", 9, 1], ["#DIV/0!", 12, 2]])
    assert result.status == "unavailable" and result.reason == "unsupported_expression"
