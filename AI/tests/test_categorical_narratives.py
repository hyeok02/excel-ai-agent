from app.services.insights.categorical_narratives import categorical_report


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


def test_measurement_tables_are_left_to_the_other_narratives() -> None:
    dated_header = [cell("C5", "항목"), cell("D5", "2024-01-31"), cell("E5", "2025-01-31")]
    rows = [dated_header] + [
        [cell(f"C{row}", name), cell(f"D{row}", 10), cell(f"E{row}", 20)]
        for row, name in enumerate(("매출", "이익", "자산", "부채", "현금"), start=6)
    ]
    assert categorical_report(context([{"title": None, "rows": rows}])) == ([], "")


def test_evidence_points_at_the_counted_cells() -> None:
    items, _ = categorical_report(context([{"title": None, "rows": [HEADER, *RECORDS]}]))
    assert all("!" in reference for reference in items[0].evidence)
    assert "'이벤트'!D7" in items[0].evidence
