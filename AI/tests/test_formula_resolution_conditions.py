from datetime import date

import pytest

from app.agent.query.formula_resolution import FormulaResolver
from tests.test_formula_resolution import workbook_index


def conditional_result(formula, rows=None):
    data = rows or [["Alpha", 10, 1], ["Beta", 20, 2], ["alpha", 30, 1], ["A*", None, 4]]
    data = [list(row) for row in data]
    data[0] = [*data[0], None, formula]
    return FormulaResolver(workbook_index(data)).resolve("Data!E1")


@pytest.mark.parametrize("formula, expected", [
    ('=SUMIF(A1:A4,"Alpha",B1:B4)', 40),
    ('=SUMIF(B1:B3,">"&B1)', 50),
    ('=SUMIFS(B1:B4,A1:A4,"Alpha",C1:C4,1)', 40),
    ('=SUMIFS(B1:B3,C1:C3,">=1",C1:C3,"<2")', 40),
    ('=COUNTIF(A1:A4,"ALPHA")', 2),
    ('=COUNTIF(A1:A4,"A*")', 3),
    ('=COUNTIF(A1:A4,"A~*")', 1),
    ('=COUNTIF(A1:A4,"?eta")', 1),
    ('=COUNTIF(A1:A4,"<>alpha")', 2),
    ('=COUNTIF(B1:B4,"")', 1),
    ('=COUNTIF(B1:B4,"<>")', 3),
    ('=COUNTIFS(A1:A4,"Alpha",C1:C4,1)', 2),
    ('=AVERAGEIF(A1:A4,"Alpha",B1:B4)', 20),
    ('=AVERAGEIFS(B1:B4,A1:A4,"Alpha",C1:C4,"=1")', 20),
    ('=SUMIF(A1:A4,"Absent",B1:B4)', 0),
    ('=IFERROR(AVERAGEIF(A1:A4,"Absent",B1:B4),99)', 99),
    ('=SUM(COUNTIF(A1:A4,"alpha"),SUMIF(A1:A4,"alpha",B1:B4))', 42),
])
def test_conditional_aggregates_have_excel_argument_order_and_matching(formula, expected):
    result = conditional_result(formula)
    assert result.status == "recovered" and result.value == expected


def test_all_criteria_and_selected_values_keep_cell_lineage():
    result = conditional_result('=SUMIFS(B1:B4,A1:A4,"Alpha",C1:C4,1)')
    assert set(result.inputs) == {f"Data!{column}{row}" for column in ("A", "C") for row in range(1, 5)} | {
        "Data!B1", "Data!B3",
    }


def test_numeric_text_criteria_coercion_is_not_guessed_and_text_amounts_are_ignored():
    result = conditional_result('=COUNTIF(A1:A3,10)', [[10, 1, 1], ["10", 2, 1], ["ten", 3, 1]])
    assert result.status == "unavailable" and result.reason == "unsupported_expression"
    result = conditional_result('=SUMIF(A1:A3,"*",B1:B3)', [["a", "10", 1], ["b", 2, 1], ["c", 3, 1]])
    assert result.value == 5


@pytest.mark.parametrize("formula", [
    '=IFERROR(SUMIFS(B1:B3,A1:A4,"Alpha"),0)',
    '=IFERROR(SUMIF(A1:A4,"Alpha",B1:C2),0)',
    '=IFERROR(COUNTIFS(A1:A4,"Alpha",C1:C3,1),0)',
    '=IFERROR(COUNTIF(B1:B4,0),0)',
    '=IFERROR(COUNTIF(A1:A4,">a"),0)',
    '=IFERROR(COUNTIF(A1:A4,TRUE),0)',
    '=IFERROR(SUMIF(A1:A4,B1:B4,B1:B4),0)',
    '=IFERROR(COUNTIF(IF(TRUE,A1:A4,0),"Alpha"),0)',
    '=IFERROR(SUMIFS(B1:B4,A1:A4),0)',
])
def test_unimplemented_coercion_shapes_and_arrays_cannot_be_hidden_by_iferror(formula):
    result = conditional_result(formula)
    assert result.status == "unavailable" and result.reason == "unsupported_expression"


@pytest.mark.parametrize("formula,rows", [
    ('=IFERROR(SUMIF(A1:A2,"Alpha",B1:B2),0)', [["Alpha", "=_xll.Remote()", 1], ["Beta", 2, 1]]),
    ('=IFERROR(COUNTIF(A1:A2,"Alpha"),0)', [["Alpha", 2, 1], ["=_xll.Remote()", 2, 1]]),
    ('=IFERROR(SUMIFS(B1:B2,A1:A2,"Absent",C1:C2,1),0)', [["Alpha", 2, "=_xll.Remote()"], ["Beta", 2, 1]]),
])
def test_unknown_external_inputs_never_become_zero_totals(formula, rows):
    result = conditional_result(formula, rows)
    assert result.status == "unavailable" and result.reason == "external_data"


def test_unselected_external_amount_does_not_block_known_filtered_total():
    result = conditional_result('=SUMIF(A1:A2,"Alpha",B1:B2)',
                                [["Alpha", 12, 1], ["Beta", "=_xll.Remote()", 1]])
    assert result.value == 12 and "Data!B2" not in result.inputs


@pytest.mark.parametrize("criterion", ['">1"', '"<10"'])
def test_numeric_text_ordering_is_not_guessed(criterion):
    result = conditional_result(f"=IFERROR(COUNTIF(A1:A2,{criterion}),99)", [["2", 1, 1], [3, 1, 1]])
    assert result.status == "unavailable" and result.reason == "unsupported_expression"


@pytest.mark.parametrize("criterion", ['"1/1/2025"', '"<>1/1/2025"', '"2025-01-01"'])
def test_date_shaped_text_criteria_do_not_invent_locale_or_zero_count(criterion):
    result = conditional_result(f"=IFERROR(COUNTIF(A1:A2,{criterion}),99)",
                                [[date(2025, 1, 1), 1, 1], [date(2025, 1, 2), 2, 1]])
    assert result.status == "unavailable" and result.reason == "unsupported_expression"


@pytest.mark.parametrize("function", ["COUNTIF", "SUMIF", "AVERAGEIF"])
def test_criteria_range_error_cells_do_not_trigger_fabricated_iferror_result(function):
    args = 'A1:A2,"Alpha"' + (",B1:B2" if function != "COUNTIF" else "")
    result = conditional_result(f"=IFERROR({function}({args}),99)",
                                [["Alpha", 12, 1], ["#N/A", 2, 1]])
    assert result.status == "unavailable" and result.reason == "unsupported_expression"


def test_nonfinite_looking_text_is_a_literal_criterion_not_a_number():
    result = conditional_result('=COUNTIF(A1:A3,"NaN")', [["NaN", 1, 1], ["nan", 1, 1], [3, 1, 1]])
    assert result.status == "recovered" and result.value == 2
