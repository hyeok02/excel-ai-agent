from app.services.insights.narratives.narrative_values import workbook_identity
from app.services.insights.facts.subject_detection import spanning_subject


def cell(address, value):
    return {"cell": address, "value": value, "number_format": None}


def span(row, text, columns=("E", "F", "G")):
    return [cell(f"{column}{row}", text) for column in columns]


def sheet(name, rows):
    return {"name": name, "business_facts": {
        "table_regions": [{"title": None, "rows": rows}],
    }}


def context(*sheets):
    return {"sheets": list(sheets)}


NAME = "International Business Machines Corporation"


def test_a_header_repeated_across_sheets_names_the_subject() -> None:
    found, evidence = spanning_subject(context(
        sheet("Income_Statement", [span(11, NAME), span(12, "NYSE:IBM")]),
        sheet("Balance_Sheet", [span(9, NAME)]),
    ))
    assert found == NAME
    assert evidence == ["'Income_Statement'!E11"]


def test_the_readable_name_wins_over_the_ticker() -> None:
    found, _ = spanning_subject(context(
        sheet("A", [span(1, NAME), span(2, "NYSE:IBM")]),
        sheet("B", [span(1, NAME), span(2, "NYSE:IBM")]),
    ))
    assert found == NAME


def test_wording_that_appears_on_one_sheet_only_is_not_a_subject() -> None:
    assert spanning_subject(context(
        sheet("A", [span(1, "Unqualified"), span(2, "FY+1")]),
        sheet("B", [span(1, "Actuals")]),
    )) == ("", [])


def test_a_run_shorter_than_three_columns_is_not_a_header() -> None:
    assert spanning_subject(context(
        sheet("A", [span(1, NAME, ("E", "F"))]),
        sheet("B", [span(1, NAME, ("E", "F"))]),
    )) == ("", [])


def test_labelled_rows_still_take_precedence() -> None:
    labelled = {
        "name": "Intermediate",
        "business_facts": {
            "selected_records": [{
                "location": "Intermediate!E6:I6",
                "values": [{"cell": "E6", "value": "Entity Name", "label": None},
                           {"cell": "I6", "value": "Bank of America Corporation (NYSE:BAC)",
                            "label": None}],
            }],
            "table_regions": [{"title": None, "rows": [span(1, NAME)]}],
        },
    }
    found, evidence = workbook_identity(context(labelled, sheet("B", [span(1, NAME)])))
    assert found == "Bank of America Corporation"
    assert evidence == ["Intermediate!E6:I6"]
