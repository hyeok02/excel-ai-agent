from copy import deepcopy

import pytest

from app.agent.query import formula_reference_package as package
from app.agent.query.formula_resolution import FormulaResolver
from app.agent.query.index import build_workbook_data_index
from tests.formula_reference_fixtures import content, patch_xml, source_book

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def resolution(data):
    return FormulaResolver(build_workbook_data_index("source.xlsx", data)).resolve("Data!F1")


@pytest.mark.parametrize("limit", ["MAX_METADATA_BYTES", "MAX_METADATA_PART_BYTES", "MAX_METADATA_ITEMS"])
def test_metadata_limits_are_fail_closed_without_breaking_plain_cell_formulas(monkeypatch, limit):
    monkeypatch.setattr(package, limit, 1)
    workbook = source_book("=IFERROR(SUM(Amounts),0)")
    assert resolution(content(workbook)).reason == "resource_limit"
    workbook["Data"]["F1"] = "=SUM(B2:B4)"
    assert resolution(content(workbook)).value == 60


@pytest.mark.parametrize("mutate", [
    lambda root: root.find(f"{_MAIN}tableColumns")[1].set("name", "region"),
    lambda root: root.set("ref", "A1:C4"),
    lambda root: root.set("headerRowCount", "2"),
    lambda root: root.set("totalsRowCount", "2"),
    lambda root: root.set("ref", "A4:D1"),
    lambda root: root.set("ref", "A1:XFE4"),
])
def test_malformed_table_geometry_and_duplicate_columns_never_produce_values(mutate):
    data = content(source_book("=IFERROR(SUM(Sales[Amount]),0)"))
    assert resolution(patch_xml(data, "xl/tables/table1.xml", mutate)).status == "unavailable"


def test_duplicate_table_relationship_is_not_arbitrarily_selected():
    data = content(source_book("=IFERROR(SUM(Sales[Amount]),0)"))
    def duplicate(root):
        parts = root.find(f"{_MAIN}tableParts")
        parts.append(deepcopy(parts[0]))
    assert resolution(patch_xml(data, "xl/worksheets/sheet1.xml", duplicate)).status == "unavailable"


def test_duplicate_casefold_defined_names_never_select_first():
    data = content(source_book("=IFERROR(SUM(Amounts),0)"))
    def duplicate(root):
        names = root.find(f"{_MAIN}definedNames")
        item = deepcopy(names[0])
        item.set("name", "amounts")
        item.text = "Data!$B$2"
        names.append(item)
    assert resolution(patch_xml(data, "xl/workbook.xml", duplicate)).status == "unavailable"


def test_external_or_traversing_table_relationships_are_never_followed():
    data = content(source_book("=IFERROR(SUM(Sales[Amount]),0)"))
    part = "xl/worksheets/_rels/sheet1.xml.rels"
    for target in ("https://invalid.example/table.xml", "../../../outside.xml"):
        changed = patch_xml(data, part, lambda root: root[0].set("Target", target))
        assert resolution(changed).status == "unavailable"
    changed = patch_xml(data, part, lambda root: root[0].set("TargetMode", "External"))
    assert resolution(changed).status == "unavailable"


def test_invalid_local_scope_invalidates_metadata_not_plain_cached_values():
    data = content(source_book("=IFERROR(SUM(Amounts),0)"))
    changed = patch_xml(data, "xl/workbook.xml", lambda root: root.find(f"{_MAIN}definedNames")[0].set("localSheetId", "-1"))
    metadata = package.read_reference_metadata(changed, {"Data"})
    assert metadata.unavailable == "unsupported_reference"


def test_defused_xml_rejects_entity_definitions():
    import io
    from zipfile import ZipFile
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("xl/workbook.xml", '<!DOCTYPE a [<!ENTITY x "boom">]><a>&x;</a>')
    assert package.read_reference_metadata(output.getvalue(), {"Data"}).unavailable == "unsupported_reference"


def test_table_calculated_column_metadata_cannot_turn_missing_formulas_into_zero():
    from xml.etree.ElementTree import SubElement
    data = content(source_book("=IFERROR(SUM(Sales[Calculated]),0)"))
    def add_formula(root):
        column = root.find(f"{_MAIN}tableColumns")[3]
        SubElement(column, f"{_MAIN}calculatedColumnFormula").text = "[@Amount]*[@Qty]"
    assert resolution(patch_xml(data, "xl/tables/table1.xml", add_formula)).status == "unavailable"


def test_cached_formula_value_remains_authoritative_when_metadata_unavailable(monkeypatch):
    data = content(source_book("=SUM(Amounts)"))
    def cache(root):
        cell = next(cell for cell in root.iter(f"{_MAIN}c") if cell.get("r") == "F1")
        cell.find(f"{_MAIN}v").text = "60"
    data = patch_xml(data, "xl/worksheets/sheet1.xml", cache)
    monkeypatch.setattr(package, "MAX_METADATA_BYTES", 1)
    recovered = resolution(data)
    assert recovered.status == "cached" and recovered.value == 60
