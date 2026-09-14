from app.services.insights.narratives.categorical_narratives import categorical_report
from app.services.insights.models import WorkbookInsightReport
from app.services.insights.verification.validator import validate_workbook_insights


def cell(address, value, number_format=None):
    return {"cell": address, "value": value, "number_format": number_format}


def context(regions):
    return {"sheets": [{"name": "이벤트", "business_facts": {"table_regions": regions}}]}


HEADER = [cell("C5", "발생일"), cell("D5", "유형"), cell("E5", "제목")]
RECORDS = [
    [cell(f"C{row}", date), cell(f"D{row}", kind), cell(f"E{row}", f"기록 {row}")]
    for row, date, kind in (
        (7, "2025-12-01", "회의"), (8, "2025-12-01", "회의"), (9, "2025-12-02", "계약"),
        (10, "2025-12-03", "회의"), (11, "2025-12-04", "점검"), (12, "2025-12-05", "계약"),
    )
]


def test_counts_records_instead_of_reciting_rows() -> None:
    items, overview = categorical_report(context([
        {"title": None, "rows": [HEADER, *RECORDS]},
    ]))
    assert items
    assert items[0].title == "유형 구성"
    assert items[0].fact == (
        "‘회의’가 6건 중 3건(50%)으로 가장 많고, 이어서 계약 2건, 점검 1건입니다."
    )
    assert "회의 3건" in items[1].fact and "계약 2건" in items[1].fact
    assert overview == items[0].fact
    assert "2025년 12월 1일부터 2025년 12월 5일까지" in items[2].fact
    assert [item.topic for item in items] == ["유형", "유형", "발생일"]


def test_header_left_in_its_own_region_still_names_the_columns() -> None:
    items, _ = categorical_report(context([
        {"title": "기록", "rows": [HEADER]},
        {"title": None, "rows": RECORDS},
    ]))
    assert items and items[0].title == "유형 구성"


def test_a_caption_above_the_table_names_what_is_recorded() -> None:
    items, _ = categorical_report(context([
        {"title": None, "rows": [[cell("C2", "일일 점검 기록")]]},
        {"title": None, "rows": [HEADER]},
        {"title": None, "rows": RECORDS},
    ]))
    assert items and items[0].title == "일일 점검 기록 구성"
    assert items[0].topic == "일일 점검 기록"
    assert "'이벤트'!C2" in items[0].evidence


def test_measurement_tables_are_left_to_the_other_narratives() -> None:
    dated_header = [cell("C5", "항목"), cell("D5", "2024-01-31"), cell("E5", "2025-01-31")]
    rows = [dated_header] + [
        [cell(f"C{row}", name), cell(f"D{row}", 10), cell(f"E{row}", 20)]
        for row, name in enumerate(("매출", "이익", "자산", "부채", "현금"), start=6)
    ]
    assert categorical_report(context([{"title": None, "rows": rows}])) == ([], "")


def test_evidence_points_at_the_whole_counted_range() -> None:
    items, _ = categorical_report(context([{"title": None, "rows": [HEADER, *RECORDS]}]))
    assert items[0].evidence == ["'이벤트'!D5", "'이벤트'!D7:D12"]
    assert items[-1].evidence == ["'이벤트'!C5", "'이벤트'!C7:C12"]


def test_caption_and_column_topics_survive_grounding_from_cited_cells() -> None:
    source = context([
        {"title": None, "rows": [[cell("C2", "일일 점검 기록")]]},
        {"title": None, "rows": [HEADER]},
        {"title": None, "rows": RECORDS},
    ])
    items, overview = categorical_report(source)
    report = validate_workbook_insights(
        WorkbookInsightReport(overview=overview, insights=items), source,
    )

    assert [item.topic for item in report.insights[:3]] == [
        "일일 점검 기록", "유형", "발생일",
    ]
