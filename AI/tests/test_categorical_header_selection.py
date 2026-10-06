from app.services.insights.facts.categorical_headers import header_index


def _cell(address, value, bold=False):
    return {"cell": address, "value": value, "bold": bold}


def test_styled_full_header_replaces_a_caption_that_spans_table_edges() -> None:
    caption = [_cell("A1", "목록"), _cell("C1", "분류")]
    header = [
        _cell("A2", "번호", True),
        _cell("B2", "설명", True),
        _cell("C2", "유형", True),
    ]
    records = [
        [_cell(f"A{row}", f"N-{row}"), _cell(f"B{row}", f"설명 {row}"),
         _cell(f"C{row}", "정상" if row < 7 else "점검")]
        for row in range(3, 9)
    ]

    assert header_index([caption, header, *records]) == 1
