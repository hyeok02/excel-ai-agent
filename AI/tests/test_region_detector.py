from openpyxl import Workbook

from app.services.region_detector import CellRegion, detect_regions


def test_detects_regions_separated_by_blank_column() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet["A1"] = "왼쪽"
    worksheet["A2"] = 10
    worksheet["D1"] = "오른쪽"
    worksheet["E1"] = 20

    regions = detect_regions(worksheet)

    assert regions == [
        CellRegion(start_cell="A1", end_cell="A2", cell_count=2),
        CellRegion(start_cell="D1", end_cell="E1", cell_count=2),
    ]
    workbook.close()


def test_does_not_connect_diagonal_cells() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet["A1"] = "첫 번째"
    worksheet["B2"] = "두 번째"

    regions = detect_regions(worksheet)

    assert regions == [
        CellRegion(start_cell="A1", end_cell="A1", cell_count=1),
        CellRegion(start_cell="B2", end_cell="B2", cell_count=1),
    ]
    workbook.close()


def test_ignores_empty_and_whitespace_cells() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet["A1"] = ""
    worksheet["B2"] = "   "

    assert detect_regions(worksheet) == []
    workbook.close()
