import pytest

from app.agent.query.formula_resolution import FormulaResolver
from tests.test_formula_resolution import workbook_index


@pytest.mark.parametrize("name", ["ROUND", "ROUNDUP", "ROUNDDOWN"])
@pytest.mark.parametrize("number, digits, expected", [
    ("1", 30, 1), ("1E100", 0, 1e100), ("1.23", 40, 1.23),
    ("1E308", 100, 1e308), ("-1.23", 40, -1.23), ("0", 100, 0),
])
def test_engine_precision_failure_cannot_be_mistaken_for_excel_error(name, number, digits, expected):
    result = FormulaResolver(workbook_index([[f"=IFERROR({name}({number},{digits}),99)"]])).resolve("Data!A1")
    assert result.status == "recovered"
    assert result.value == expected


@pytest.mark.parametrize("name, expected", [
    ("SUM", 10), ("COUNT", 1), ("AVERAGE", 10), ("MIN", 10), ("MAX", 10), ("COUNTA", 3),
])
def test_indirect_array_retains_reference_text_and_boolean_rules(name, expected):
    index = workbook_index([[10, f"={name}(IF(TRUE,A1:A3,0))"], [True], ["20"]])
    result = FormulaResolver(index).resolve("Data!B1")
    assert result.status == "recovered"
    assert result.value == expected


@pytest.mark.parametrize("expression", [
    "SUM(IFERROR(A1:A3,0))", "AVERAGE(IFERROR(A1:A3,0))", "IFERROR(A1:A3,99)",
    "IFERROR(IF(TRUE,A1:A3,0),99)", "IFERROR(A1:A3+1,99)", "IFERROR(-A1:A3,99)",
    "IFERROR(ROUND(A1:A3,2),99)", "IFERROR(ABS(A1:A3),99)",
    "IFERROR(IF(A1:A3>0,1,0),99)", "IFERROR(1,A1:A3)",
])
def test_array_iferror_fails_closed_before_eager_evaluation(expression):
    result = FormulaResolver(workbook_index([[10, "=" + expression], ["#DIV/0!"], [20]])).resolve("Data!B1")
    assert result.status == "unavailable" and result.value is None
    assert result.reason == "unsupported_expression"


def test_genuine_scalar_excel_error_still_uses_iferror_fallback():
    result = FormulaResolver(workbook_index([[10, "=IFERROR(SUM(A1:A3),99)"], ["#DIV/0!"], [20]])).resolve("Data!B1")
    assert result.status == "recovered" and result.value == 99


def test_engine_numeric_bound_is_not_treated_as_excel_error():
    result = FormulaResolver(workbook_index([["=IFERROR(1.5E308*1,99)"]])).resolve("Data!A1")
    assert result.status == "unavailable" and result.reason == "unsupported_expression"
