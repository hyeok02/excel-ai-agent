from dataclasses import replace

import pytest

from app.agent.query.formula_resolution import FormulaResolver
from app.agent.query.formula_resolution_models import FormulaLimits
from tests.test_formula_resolution import workbook_index


@pytest.mark.parametrize("formula, reason", [
    ("='[other.xlsx]Data'!A1+1", "external_data"),
    ('=IFERROR(_xll.CIQ("ABC","IQ_TOTAL_DEBT"),0)', "external_data"),
    ('=IFERROR(WEBSERVICE("https://invalid.example"),0)', "external_data"),
    ("=IFERROR(Missing!A1,0)", "missing_reference"),
    ("=IFERROR(INDIRECT(\"A1\"),0)", "unsupported_function"),
    ("=NOW()", "unsupported_function"),
    ("=RAND()", "unsupported_function"),
    ("=TotalAmount", "unsupported_reference"),
    ("=SUM(Table1[Amount])", "unsupported_reference"),
    ("=SUM(A:A)", "unsupported_reference"),
    ("=A1 B1", "unsupported_expression"),
    ("=SUM(A1,A2", "unsupported_expression"),
    ("=1/0", "calculation_error"),
    ("=IFERROR(2^.5,0)", "unsupported_expression"),
    ("=IFERROR(YEAR(45000),0)", "unsupported_expression"),
    ("=DATE(2026,5,4)", "unsupported_expression"),
    ("=IFERROR(SUM(DATE(2026,5,4)),0)", "unsupported_expression"),
    ("=IFERROR(AND(A1:A2),0)", "unsupported_expression"),
    ("=IFERROR(TRUE=1,0)", "unsupported_expression"),
])
def test_unknown_data_never_becomes_zero(formula, reason):
    result = FormulaResolver(workbook_index([["text", formula], [True]])).resolve("Data!B1")
    assert result.status == "unavailable"
    assert result.value is None
    assert result.reason == reason
    assert result.message


def test_source_error_and_missing_external_dependency_are_distinct():
    resolver = FormulaResolver(workbook_index([["#DIV/0!", "=A1+1", "=IFERROR(A1,7)"]]))
    assert resolver.resolve("Data!B1").reason == "source_error"
    assert resolver.resolve("Data!C1").value == 7
    external = FormulaResolver(workbook_index([["=_xll.RemoteValue()", "=IFERROR(A1,0)"]]))
    result = external.resolve("Data!B1")
    assert result.reason == "external_data"
    assert result.missing_references == ("_XLL.REMOTEVALUE",)
    assert "Data!A1" in result.inputs


def test_cycles_are_reported_and_do_not_poison_other_formulas():
    resolver = FormulaResolver(workbook_index([["=B1", "=A1", "=2+3"]]))
    assert resolver.resolve("Data!A1").reason == "cycle"
    assert resolver.resolve("Data!C1").value == 5


@pytest.mark.parametrize("limits, formula", [
    (FormulaLimits(max_range_cells=4), "=SUM(A1:A5)"),
    (FormulaLimits(max_tokens=2), "=1+2+3"),
    (FormulaLimits(max_depth=2), "=(((1+2)))"),
    (FormulaLimits(max_formula_length=4), "=SUM(A1)"),
    (FormulaLimits(max_cells=2), "=SUM(A1:A3)"),
    (FormulaLimits(timeout_seconds=0), "=1+2"),
    (FormulaLimits(max_result_characters=4), '="abc"&"def"'),
])
def test_resource_limits(limits, formula):
    result = FormulaResolver(workbook_index([[1, formula], [2], [3]]), limits).resolve("Data!B1")
    assert result.reason == "resource_limit"


def test_truncated_index_does_not_assume_missing_inputs_are_blank():
    index = replace(workbook_index([[1, "=SUM(A1:A10)"]]), truncated=True,
                    truncated_sheet_names=frozenset({"Data"}))
    assert FormulaResolver(index).resolve("Data!B1").reason == "index_truncated"


def test_formula_count_limit_keeps_unavailable_metadata():
    resolver = FormulaResolver(workbook_index([["=1", "=2"]]), FormulaLimits(max_formulas=1))
    results = resolver.resolve_all()
    assert results[0].value == 1
    assert results[1].reason == "resource_limit"


def test_known_conditional_can_skip_unselected_external_branch():
    result = FormulaResolver(workbook_index([["=IF(1=1,7,_xll.RemoteValue())"]])).resolve("Data!A1")
    assert result.value == 7


def test_untrusted_formula_cannot_run_python_or_shell():
    formula = '=__import__("os").system("echo unexpected")'
    result = FormulaResolver(workbook_index([[formula]])).resolve("Data!A1")
    assert result.status == "unavailable" and result.value is None


def test_repeated_concatenation_stays_bounded():
    resolver = FormulaResolver(workbook_index([["abc", "=A1&A1", "=B1&B1", "=C1&C1"]]),
                               FormulaLimits(max_result_characters=10))
    assert resolver.resolve("Data!D1").reason == "resource_limit"
