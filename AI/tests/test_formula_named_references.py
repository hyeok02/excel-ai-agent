from dataclasses import replace
from hashlib import sha256

import pytest
from openpyxl.workbook.defined_name import DefinedName

from app.agent.query.formula_resolution import FormulaResolver
from app.agent.query.formula_resolution_models import FormulaLimits
from app.agent.query.index import WorkbookDataIndex, build_workbook_data_index
from tests.formula_reference_fixtures import content, result, source_book


@pytest.mark.parametrize("formula, expected", [
    ("=SUM(Amounts)", 60), ("=SUM(amounts)", 60), ("=OneAmount*2", 20),
    ('=SUMIF(Regions,"East",Amounts)', 40), ('=SUMIFS(Amounts,Regions,"East")', 40),
    ('=COUNTIF(Amounts,">15")', 2), ('=AVERAGEIF(Regions,"East",Amounts)', 20),
    ('=XLOOKUP("West",Regions,Amounts)', 20), ('=INDEX(Amounts,2)', 20),
    ('=MATCH(20,Amounts,0)', 2), ('=SUM(\'Other sheet\'!Amounts)', 100),
])
def test_named_ranges_work_in_aggregates_lookup_and_arithmetic(formula, expected):
    recovered = result(source_book(formula))
    assert recovered.status == "recovered"
    assert recovered.value == expected
    assert recovered.inputs


def test_local_name_shadows_global_case_insensitively():
    workbook = source_book()
    workbook["Other sheet"]["C1"] = "=SUM(aMoUnTs)"
    assert result(workbook, "Other sheet!C1").value == 100


def test_named_input_lineage_and_source_bytes_are_preserved():
    workbook = source_book()
    before = content(workbook)
    index = build_workbook_data_index("source.xlsm", before)
    recovered = FormulaResolver(index).resolve("Data!F1")
    assert recovered.inputs == ("Data!B2", "Data!B3", "Data!B4")
    assert next(cell for row in index.rows for cell in row.cells if cell.address == "F1").value is None
    assert index.source_digest == sha256(before).hexdigest()
    assert replace(index, filename="renamed.xlsx").source_digest == index.source_digest
    assert WorkbookDataIndex("old", (), 0, False).source_digest == ""
    workbook["Data"]["B2"] = 11
    assert build_workbook_data_index("source.xlsm", content(workbook)).source_digest != index.source_digest


@pytest.mark.parametrize("target", [
    "Data!B2:B4", "Data!$B2:$B4", "Data!$B$2,Data!$B$4", "OtherAlias",
    "OFFSET(Data!$B$2,0,0,3,1)", "42", '"text"', "Data:Hidden!$B$2",
    "Data!$B:$B", "Data!$B$4:$B$2",
])
def test_dynamic_relative_union_and_non_reference_names_are_not_guessed(target):
    workbook = source_book("=IFERROR(SUM(Unsafe),0)")
    workbook.defined_names.add(DefinedName("Unsafe", attr_text=target))
    recovered = result(workbook)
    assert recovered.status == "unavailable" and recovered.value is None


@pytest.mark.parametrize("target", ["'[remote.xlsx]Data'!$B$2", "Missing!$B$2"])
def test_external_and_absent_named_sources_are_not_zero(target):
    workbook = source_book("=IFERROR(SUM(Unsafe),0)")
    workbook.defined_names.add(DefinedName("Unsafe", attr_text=target))
    assert result(workbook).status == "unavailable"


def test_excluded_named_source_is_unavailable_and_hidden_name_keeps_local_scope():
    workbook = source_book()
    workbook["Other sheet"]["C1"] = "=SUM(Regions)"
    assert result(workbook, "Other sheet!C1", included={"Other sheet"}).status == "unavailable"
    workbook["Other sheet"].defined_names["Amounts"].hidden = True
    workbook["Other sheet"]["C1"] = "=IFERROR(SUM(Amounts),0)"
    assert result(workbook, "Other sheet!C1").value == 100


def test_hidden_sheet_respects_explicit_included_sheet_boundary():
    workbook = source_book("=SUM(Secret)")
    workbook.defined_names.add(DefinedName("Secret", attr_text="Hidden!$A$1"))
    assert result(workbook, included={"Data", "Hidden"}).value == 777
    assert result(workbook, included={"Data"}).status == "unavailable"


def test_duplicate_casefold_name_and_name_cycle_are_unavailable():
    workbook = source_book()
    workbook.defined_names.add(DefinedName("amounts", attr_text="Data!$B$2"))
    assert result(workbook).status == "unavailable"
    workbook = source_book("=IFERROR(Loop,0)")
    workbook.defined_names.add(DefinedName("Loop", attr_text="Data!$F$1"))
    assert result(workbook).reason == "cycle"


def test_named_ranges_obey_range_and_truncation_budgets():
    workbook = source_book()
    assert result(workbook, limits=FormulaLimits(max_range_cells=2)).reason == "resource_limit"
    index = build_workbook_data_index("x.xlsx", content(workbook))
    index = replace(index, truncated=True, truncated_sheet_names=frozenset({"Data"}))
    assert FormulaResolver(index).resolve("Data!F1").reason == "index_truncated"


@pytest.mark.parametrize("formula", ["=IFERROR(Amounts,0)", "=IFERROR(Amounts+1,0)", '=IFERROR(MATCH(Amounts,Amounts,0),0)'])
def test_array_named_ranges_cannot_be_scalarized_by_iferror(formula):
    workbook = source_book(formula)
    workbook["Data"]["B2"] = "#DIV/0!"
    assert result(workbook).status == "unavailable"
