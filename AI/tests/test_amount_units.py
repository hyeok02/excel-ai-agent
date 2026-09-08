from app.services.insights.display.amount_units import amount_unit


def cell(address, value):
    return {"cell": address, "value": value, "number_format": None}


def sheet(rows, name="Key_Stats"):
    return {"name": name, "business_facts": {
        "table_regions": [{"title": None, "rows": rows}],
    }}


def test_a_note_over_the_table_states_the_unit() -> None:
    text, evidence = amount_unit(sheet([[cell("B51", "(in $ Millions, except per share)")]]))
    assert text == "백만 달러"
    assert evidence == ["'Key_Stats'!B51"]


def test_the_value_under_each_label_states_the_unit() -> None:
    text, evidence = amount_unit(sheet([
        [cell("F17", "Currency"), cell("H17", "Magnitude")],
        [cell("F18", "U.S. Dollar"), cell("H18", "Millions")],
    ]))
    assert text == "백만 달러"
    assert evidence == ["'Key_Stats'!H18", "'Key_Stats'!F18"]


def test_a_dropdown_list_of_choices_is_never_read_as_the_selection() -> None:
    assert amount_unit(sheet([
        [cell("B4", "Currency")],
        [cell("B5", "Magnitude")],
        [cell("B8", "Thousands")],
        [cell("B9", "Millions")],
        [cell("B10", "Billions")],
    ])) == ("", [])


def test_a_magnitude_without_a_currency_is_not_reported() -> None:
    assert amount_unit(sheet([
        [cell("H17", "Magnitude")],
        [cell("H18", "Millions")],
    ])) == ("", [])


def test_a_sheet_that_states_nothing_reports_nothing() -> None:
    assert amount_unit(sheet([[cell("B2", "매출"), cell("C2", 100)]])) == ("", [])
