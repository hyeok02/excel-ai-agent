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


def test_first_data_label_inferred_as_region_title_is_not_the_table_owner() -> None:
    context = {"sheets": [{"name": "Measures", "business_facts": {"table_regions": [{
        "title": "Purchased power",
        "rows": [
            [_cell("A7", "Purchased power"), _cell("B7", 80), _cell("C7", 60)],
            [_cell("A14", "All energy"), _cell("B14", 300), _cell("C14", 240)],
        ],
    }]}}]}

    assert visible_subject(context, {"measures!a14:c14"}) == ""


def test_standalone_region_title_still_names_the_table_owner() -> None:
    context = {"sheets": [{"name": "Measures", "business_facts": {"table_regions": [{
        "title": "North Research Institute",
        "rows": [
            [_cell("A1", "North Research Institute"), _cell("B1", None)],
            [_cell("A7", "Purchased power"), _cell("B7", 80)],
        ],
    }]}}]}

    assert visible_subject(context, {"measures!b7"}) == "North Research Institute"
