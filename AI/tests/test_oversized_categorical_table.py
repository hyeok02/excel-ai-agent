"""Regression coverage for wide record tables with captions and hidden duplicates."""
from dataclasses import asdict

from openpyxl import Workbook
from openpyxl.styles import Font

from app.services.insights.facts.business_facts import build_business_facts
from app.services.insights.narratives.categorical_narratives import categorical_report
from app.services.insights.narratives.source_narratives import source_narrative_report
from app.services.insights.verification.validator import validate_workbook_insights
from app.services.region_detector import CellRegion
from app.services.semantic_models import SemanticClassification, SemanticRole
from app.services.workbook_details.regions import summarize_regions


DATA = SemanticClassification(role=SemanticRole.DATA, confidence=1.0)
KOREAN = ["CVD"] * 36 + ["냉각수"] * 27 + ["진공펌프"] * 10 + ["Data Tag"] * 2
JAPANESE = ["CVD"] * 36 + ["冷却水"] * 27 + ["真空ポンプ"] * 10 + ["Data Tag"] * 2


def test_wide_sparse_region_is_counted_from_all_visible_rows() -> None:
    workbook = _wide_workbook()
    try:
        sheet = workbook.active
        region = summarize_regions(
            sheet, [CellRegion("B3", "AU81", 1_642, DATA)]
        )[0]

        assert (region.row_count, region.column_count) == (79, 46)
        assert region.is_truncated
        assert region.analysis_complete
        assert region.hidden_rows == []
        assert region.hidden_columns == ["E", "F", "G", "H"]

        facts = build_business_facts("설비", [asdict(region)], [], 12)
        [table] = facts["table_regions"]
        assert table["analysis_complete"]
        assert table["rows_complete"]
        assert table["hidden_columns"] == ["E", "F", "G", "H"]
        _assert_correct_report(*categorical_report(_context(facts)))
    finally:
        workbook.close()


def test_table_budget_clipping_never_publishes_partial_counts() -> None:
    rows = [
        [_cell(f"{column}{row}", f"값-{row % 3}") for column in "ABCDEFGHIJ"]
        for row in range(1, 301)
    ]
    region = {
        "analysis_rows": rows, "analysis_complete": True,
        "preview_rows": rows[:8], "is_truncated": True,
        "hidden_rows": [], "hidden_columns": [],
    }
    facts = build_business_facts("설비", [region], [], max_records=12)
    [table] = facts["table_regions"]

    assert table["analysis_complete"]
    assert not table["rows_complete"]
    assert categorical_report(_context(facts)) == ([], "")


def test_distant_same_sheet_identity_does_not_rename_the_visible_report() -> None:
    workbook = _wide_workbook()
    try:
        region = summarize_regions(
            workbook.active, [CellRegion("B3", "AU81", 1_642, DATA)]
        )[0]
        facts = build_business_facts("설비", [asdict(region)], [], 12)
        facts["selected_records"].insert(0, {
            "location": "설비!Y1:AB1", "values": [
                {"cell": "Y1", "value": "분석 대상"},
                {"cell": "AB1", "value": "PLC Alarm"},
            ],
        })
        context = _context(facts)
        draft = source_narrative_report(context)
        result = validate_workbook_insights(draft, context)

        assert "PLC Alarm" not in result.overview
        assert "기록 75건" in result.overview
    finally:
        workbook.close()


def _assert_correct_report(items, overview) -> None:
    assert items
    assert (items[0].title, items[0].topic) == ("대항목 구성", "대항목")
    assert "‘CVD’가 75건 중 36건(48%)" in overview
    assert "냉각수 27건" in overview
    assert "진공펌프 10건" in overview
    assert items[0].evidence == ["'설비'!I6", "'설비'!I7:I81"]
    assert "Data Tag’이 5건 중" not in overview
    assert "大項目 1건" not in overview
    assert all("!F" not in evidence for item in items for evidence in item.evidence)


def _wide_workbook() -> Workbook:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "설비"
    for column in ("E", "F", "G", "H"):
        sheet.column_dimensions[column].hidden = True
    _intro_and_header(sheet)
    for row, (korean, japanese) in enumerate(zip(KOREAN, JAPANESE), start=7):
        _record(sheet, row, korean, japanese)
    sheet["AU81"] = 1
    return workbook


def _intro_and_header(sheet) -> None:
    for address, value in (("C3", "작업대기상태 DATA"), ("C4", "TAG 안내"),
                           ("F4", "분류分類"), ("I4", "분류分類"),
                           ("C5", "TAG 작성 규칙")):
        sheet[address] = value
    for column, value in zip("BCDEFGHI", (
        "NO", "TAG", "설명", "説明", "대항목\n大項目", "중항목", "소항목", "대항목\n大項目",
    )):
        sheet[f"{column}6"] = value
        sheet[f"{column}6"].font = Font(bold=True)


def _record(sheet, row: int, korean: str, japanese: str) -> None:
    values = (row - 7, f"TAG-{row}", f"설명 {row}", f"説明 {row}", japanese,
              f"중항목-{row}", f"소항목-{row}", korean)
    for column, value in zip("BCDEFGHI", values):
        sheet[f"{column}{row}"] = value


def _cell(address: str, value: object) -> dict[str, object]:
    return {"address": address, "value": value, "formula": None,
            "cached_value": None, "number_format": "General"}


def _context(facts: dict[str, object]) -> dict[str, object]:
    return {"sheets": [{"name": "설비", "business_facts": facts}]}
