from app.services.insights.narratives.categorical_narratives import categorical_report


def _cell(address, value):
    return {"cell": address, "value": value, "number_format": None}


def test_explicit_classification_beats_a_near_constant_state_column() -> None:
    header = [_cell("A1", "상태"), _cell("B1", "분류")]
    categories = ("CVD", "냉각수", "진공", "기타") * 5
    records = [
        [_cell(f"A{row}", "정상" if row < 21 else "점검"),
         _cell(f"B{row}", category)]
        for row, category in enumerate(categories, 2)
    ]
    context = {"sheets": [{"name": "현황", "business_facts": {
        "table_regions": [{"title": None, "rows": [header, *records]}],
    }}]}

    items, overview = categorical_report(context)

    assert items and items[0].title == "분류 구성"
    assert "20건 중 5건(25%)" in overview


def test_balanced_classification_beats_a_near_constant_type_column() -> None:
    header = [_cell("A1", "대항목"), _cell("B1", "TYPE")]
    categories = ("CVD", "냉각수", "진공", "기타") * 5
    records = [
        [_cell(f"A{row}", category),
         _cell(f"B{row}", "16 Bit DEC" if row < 21 else "ASCII")]
        for row, category in enumerate(categories, 2)
    ]
    context = {"sheets": [{"name": "현황", "business_facts": {
        "table_regions": [{"title": None, "rows": [header, *records]}],
    }}]}

    items, overview = categorical_report(context)

    assert items and items[0].title == "대항목 구성"
    assert "20건 중 5건(25%)" in overview
