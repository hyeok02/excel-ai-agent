import pytest

from app.agent.query.formula_resolution_models import FormulaLimits
from tests.formula_reference_fixtures import result, source_book


@pytest.mark.parametrize("formula, expected", [
    ("=SUM(Sales[Amount])", 60), ("=SUM(sales[amount])", 60), ("=SUM(Sales)", 69),
    ('=SUMIF(Sales[Region],"East",Sales[Amount])', 40),
    ('=SUMIFS(Sales[Amount],Sales[Region],"East")', 40),
    ('=COUNTIFS(Sales[Region],"East",Sales[Qty],">2")', 1),
    ('=XLOOKUP("West",Sales[Region],Sales[Amount])', 20),
    ('=VLOOKUP("West",Sales,2,FALSE)', 20),
    ('=SUM(Sales[[Amount]:[Qty]])', 69),
    ('=SUM(Sales[[#Data],[Amount]:[Qty]])', 69),
    ('=SUM(Sales[[#Data],[Amount]])', 60),
    ('=COUNTA(Sales[#Headers])', 4),
    ('=Sales[[#Headers],[Amount]]', "Amount"),
])
def test_structured_reference_shapes_are_shared_by_supported_functions(formula, expected):
    recovered = result(source_book(formula))
    assert recovered.status == "recovered" and recovered.value == expected


@pytest.mark.parametrize("formula, expected", [
    ("=SUM(Sales[Amount])", 60), ("=SUM(Sales[#Data])", 69),
    ("=SUM(Sales[[#Totals],[Amount]])", 60), ("=SUM(Sales[[#All],[Amount]])", 120),
])
def test_totals_are_excluded_by_default_and_only_included_explicitly(formula, expected):
    assert result(source_book(formula, totals=True)).value == expected


@pytest.mark.parametrize("formula", [
    "=[@Amount]*[@Qty]", "=[@[Amount]]*[@[Qty]]", "=Sales[@Amount]*Sales[@Qty]",
    "=Sales[[#This Row],[Amount]]*Sales[[#This Row],[Qty]]",
])
def test_current_row_uses_each_formula_address_and_preserves_lineage(formula):
    workbook = source_book("=SUM(Sales[Calculated])")
    workbook["Data"]["D2"] = formula
    workbook["Data"]["D3"] = formula
    recovered = result(workbook)
    assert recovered.status == "recovered" and recovered.value == 80
    assert {"Data!B2", "Data!C2", "Data!B3", "Data!C3", "Data!D2", "Data!D3"} <= set(recovered.inputs)


def test_unqualified_whole_column_ref_inside_table_is_supported():
    workbook = source_book()
    workbook["Data"]["D2"] = "=SUM([Amount])"
    assert result(workbook, "Data!D2").value == 60


@pytest.mark.parametrize("header, token", [
    ("매출액", "[매출액]"), ("Amount [USD]", "[Amount '[USD']]"), ("Profit!Amount", "[Profit!Amount]"),
    ("#Amount", "['#Amount]"), ("@Amount", "['@Amount]"), ("Owner's", "[Owner''s]"),
])
def test_column_names_are_bound_from_source_not_business_keywords(header, token):
    workbook = source_book(f"=SUM(Sales{token})", headers=["Region", header, "Qty", "Calculated"])
    assert result(workbook).value == 60


@pytest.mark.parametrize("header, token", [("Price#", "[Price#]"), ("Owner's", "[Owner's]")])
def test_unescaped_special_header_syntax_is_not_guessed(header, token):
    workbook = source_book(f"=IFERROR(SUM(Sales{token}),0)", headers=["Region", header, "Qty", "Calculated"])
    assert result(workbook).status == "unavailable"


@pytest.mark.parametrize("formula", [
    "=IFERROR(SUM(Missing[Amount]),0)", "=IFERROR(SUM(Sales[Missing]),0)",
    "=IFERROR(Sales[@Amount],0)", "=IFERROR(Sales[[#Totals],[Amount]],0)",
    "=IFERROR(Sales[[#Headers],[#Data],[Amount]],0)", "=IFERROR(SUM([Amount]),0)",
    "=IFERROR(Sales[[Qty]:[Amount]],0)", "=IFERROR(Sales[Amount],0)",
    "=IFERROR(SUM(Sales[[Amount],[Qty]]),0)",
])
def test_unknown_nonrectangular_or_invalid_row_context_is_not_masked(formula):
    recovered = result(source_book(formula))
    assert recovered.status == "unavailable" and recovered.value is None


def test_current_row_does_not_cross_sheets_or_totals_and_cycles_are_detected():
    workbook = source_book(totals=True)
    workbook["Other sheet"]["C2"] = "=Sales[@Amount]"
    workbook["Data"]["D5"] = "=[@Amount]"
    assert result(workbook, "Other sheet!C2").status == "unavailable"
    assert result(workbook, "Data!D5").status == "unavailable"
    workbook["Data"]["D2"] = "=IFERROR([@Calculated],0)"
    assert result(workbook, "Data!D2").reason == "cycle"


def test_excluded_table_sources_and_large_ranges_are_unavailable():
    workbook = source_book()
    workbook["Other sheet"]["C2"] = "=IFERROR(SUM(Sales[Amount]),0)"
    assert result(workbook, "Other sheet!C2", included={"Other sheet"}).status == "unavailable"
    workbook["Data"]["F1"] = "=SUM(Sales)"
    assert result(workbook, limits=FormulaLimits(max_range_cells=5)).reason == "resource_limit"
