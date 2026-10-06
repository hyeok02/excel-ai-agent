"""다른 언어·다른 표식으로 쓰인 점검표도 같은 규칙으로 읽는지 검증한다."""
from app.services.insights.narratives.flag_narratives import flag_matrix_report
AUDIT_HEADERS = ("Store Code", "Branch", "Fire Safety", "Food Licence", "Signage")
AUDIT_ROWS = [
    ("S-01", "Lisbon Alfama", "✓", "✗", "✓"),
    ("S-02", "Lisbon Belem", "✓", "✓", "✗"),
    ("S-03", "Porto Centro", "✗", "✓", "✓"),
    ("S-04", "Porto Foz", "✓", "✓", "✓"),
    ("S-05", "Faro Marina", "△ (awaiting inspector, booked 12 Nov)", "✗", "✓"),
    ("S-06", "Braga Norte", "✓", "✓", "✓"),
    ("S-07", "Coimbra Velha", None, None, None),
]


def _audit_context():
    table = [[{"cell": f"{column}1", "value": value}
              for column, value in zip("ABCDE", AUDIT_HEADERS)]]
    for number, values in enumerate(AUDIT_ROWS, start=2):
        table.append([{"cell": f"{column}{number}", "value": value}
                      for column, value in zip("ABCDE", values) if value is not None])
    return {"omitted_sheet_count": 0, "sheets": [{
        "name": "Audit",
        "business_facts": {"table_rows": table, "selected_records": [],
                           "numeric_changes": [], "time_series": []},
    }]}


def test_reads_a_checklist_written_in_another_language_and_other_marks() -> None:
    items, _ = flag_matrix_report(_audit_context())

    assert items[0].title == "Branch 점검 현황"
    assert "‘Fire Safety’, ‘Food Licence’, ‘Signage’ 3가지" in items[0].fact
    assert "6건이 점검됐고 1건은" in items[0].fact


def test_reports_marks_as_the_sheet_writes_them() -> None:
    items, _ = flag_matrix_report(_audit_context())
    column = next(item for item in items if item.title == "Fire Safety 표시")

    assert "✓ 4건" in column.fact and "✗ 1건" in column.fact and "△ 1건" in column.fact
    assert "v " not in column.fact and "x " not in column.fact


def test_picks_the_particle_from_the_name_it_just_wrote() -> None:
    items, _ = flag_matrix_report(_audit_context())

    assert "‘Food Licence’가 ✗인 건이 2건으로 가장 많습니다" in items[0].fact


def test_subject_falls_back_to_the_header_when_rows_share_no_prefix() -> None:
    items, _ = flag_matrix_report(_audit_context())

    assert items[0].title.startswith("Branch")
