"""점검표(o/x 표식) 시트를 그 자체로 설명하는지 검증한다."""
from app.services.insights.facts.flag_columns import blank_records, flag_matrix
from app.services.insights.narratives.flag_narratives import flag_matrix_report
from app.services.insights.quality import build_source_report
from app.services.insights.verification.validator import validate_workbook_insights

HEADERS = ("IP", "장비", "작업", "네트워크 안정", "자료 유무")
ROWS = [
    ("10.0.0.1", "CVD #1", "o", "x", "o"),
    ("10.0.0.2", "CVD #2", "o", "x", "o"),
    ("10.0.0.3", "CVD #3", "o", "o", "o"),
    ("10.0.0.4", "CVD #4", "o", "o", "o"),
    ("10.0.0.5", "CVD #5", "△(방화벽 해제 필요)", "?", "o"),
    ("10.0.0.6", "CVD #6", None, None, None),
    ("10.0.0.7", "CVD #7", None, None, None),
]


def _rows():
    table = [[{"cell": f"{column}1", "value": value}
              for column, value in zip("ABCDE", HEADERS)]]
    for number, values in enumerate(ROWS, start=2):
        table.append([{"cell": f"{column}{number}", "value": value}
                      for column, value in zip("ABCDE", values)
                      if value is not None])
    return table


def _context():
    return {"omitted_sheet_count": 0, "sheets": [{
        "name": "작업현황",
        "business_facts": {"table_rows": _rows(), "selected_records": [],
                           "numeric_changes": [], "time_series": []},
    }]}


def test_detects_neighbouring_mark_columns_and_their_label() -> None:
    rows = _rows()
    label, run = flag_matrix(rows[0], rows[1:])

    assert label["value"] == "장비"
    assert [cell["value"] for _, cell, _, _ in run] == [
        "작업", "네트워크 안정", "자료 유무",
    ]


def test_counts_rows_with_no_mark_at_all_as_unchecked() -> None:
    rows = _rows()
    _, run = flag_matrix(rows[0], rows[1:])

    assert len(blank_records(rows[1:], run)) == 2


def test_reads_a_long_note_by_the_mark_it_starts_with() -> None:
    rows = _rows()
    _, run = flag_matrix(rows[0], rows[1:])
    counts = next(counts for _, cell, counts, _ in run if cell["value"] == "작업")

    assert counts["o"] == 4
    assert counts["△"] == 1


def test_names_the_subject_from_the_rows_not_the_column_header() -> None:
    items, _ = flag_matrix_report(_context())

    assert items[0].title == "CVD 장비 점검 현황"


def test_head_names_the_checks_and_where_the_work_stalls() -> None:
    items, overview = flag_matrix_report(_context())

    assert "‘작업’, ‘네트워크 안정’, ‘자료 유무’ 3가지" in items[0].fact
    assert "5건이 점검됐고 2건은 아직 아무 항목도 표시되지 않았습니다" in items[0].fact
    assert "‘네트워크 안정’이 x인 건이 2건으로 가장 많습니다" in items[0].fact
    assert overview


def test_overview_adds_a_check_the_head_has_not_named() -> None:
    items, overview = flag_matrix_report(_context())

    assert "‘네트워크 안정’은 기재된" not in overview


def test_each_column_reports_its_marks_and_its_blanks() -> None:
    items, _ = flag_matrix_report(_context())
    column = next(item for item in items if item.title == "네트워크 안정 표시")

    assert "x 2건" in column.fact and "o 2건" in column.fact and "? 1건" in column.fact
    assert "2건은 비어 있습니다" in column.fact
    assert column.evidence == ["'작업현황'!D1", "'작업현황'!D2:D6"]


def test_lead_says_the_file_is_a_checklist() -> None:
    context = _context()
    result = validate_workbook_insights(build_source_report(context), context)

    assert result.overview.startswith(
        "이 파일은 CVD 장비 7건을 ‘작업’, ‘네트워크 안정’, ‘자료 유무’ 3가지 항목으로 "
        "점검한 표입니다."
    )


def test_plain_record_tables_are_left_to_other_narratives() -> None:
    rows = [[{"cell": f"{c}1", "value": v} for c, v in zip("ABC", ("이름", "부서", "직급"))]]
    for number, values in enumerate(
        [("가","영업","사원"),("나","영업","대리"),("다","개발","사원"),
         ("라","개발","과장"),("마","인사","사원")], start=2):
        rows.append([{"cell": f"{c}{number}", "value": v}
                     for c, v in zip("ABC", values)])

    assert flag_matrix(rows[0], rows[1:]) is None
