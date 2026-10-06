from openpyxl import Workbook

from app.services.workbook_details import analysis_samples
from app.services.workbook_details.analysis_samples import collect_analysis_sample


def test_very_tall_sparse_region_is_analyzed_from_stored_cells() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet["A1"] = "항목"
    sheet["A100000"] = "완료"
    try:
        rows, complete = collect_analysis_sample(
            sheet, None, (1, 1, 1, 100000), 2048,
        )
        assert complete
        assert [[cell["address"] for cell in row] for row in rows] == [
            ["A1"], ["A100000"],
        ]
    finally:
        workbook.close()


def test_hidden_columns_do_not_consume_the_visible_scan_budget(monkeypatch) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet["A1"], sheet["B2"], sheet["A3"] = "시작", "숨김", "끝"
    monkeypatch.setattr(analysis_samples, "MAX_ANALYSIS_SCAN_CELLS", 2)
    try:
        rows, complete = collect_analysis_sample(
            sheet, None, (1, 1, 2, 3), 2048, hidden_columns={"B"},
        )
        assert complete
        assert [[cell["address"] for cell in row] for row in rows] == [
            ["A1"], ["A3"],
        ]
    finally:
        workbook.close()
