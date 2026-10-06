from app.services.insights.narratives.subject_scope import visible_subject


def _cell(address, value):
    return {"cell": address, "value": value, "number_format": None}


def _sheet(name, row, value):
    return {"name": name, "business_facts": {"table_regions": [{
        "title": None,
        "rows": [[_cell(f"{column}{row}", value) for column in "IJK"]],
    }]}}


def test_repeated_data_value_inside_evidence_is_not_a_subject() -> None:
    context = {"sheets": [
        _sheet("A", 7, "Data Tag"),
        _sheet("B", 7, "Data Tag"),
    ]}

    assert visible_subject(context, {"a!i7:i81"}) == ""


def test_repeated_header_above_evidence_remains_a_subject() -> None:
    context = {"sheets": [
        _sheet("A", 1, "Sample Company"),
        _sheet("B", 1, "Sample Company"),
    ]}

    assert visible_subject(context, {"a!i5:i20"}) == "Sample Company"
