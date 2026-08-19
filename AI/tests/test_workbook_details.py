from openpyxl import Workbook
from openpyxl.workbook.defined_name import DefinedName

from app.services.workbook_details import _resolve_reference_values


def test_resolves_chart_series_backed_by_offset_defined_name() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Chart_Data"
    worksheet["C1"] = 3
    worksheet["A1"] = "시작"
    worksheet["A2"] = "1월"
    worksheet["A3"] = "2월"
    worksheet["A4"] = "3월"
    workbook.defined_names.add(
        DefinedName(
            "Dates",
            attr_text="OFFSET(Chart_Data!$A$1,1,0,Chart_Data!$C$1,1)",
        )
    )

    try:
        assert _resolve_reference_values(workbook, "[0]!Dates", 12) == [
            "1월",
            "2월",
            "3월",
        ]
    finally:
        workbook.close()
