from app.services.insights.facts.business_facts import build_business_facts
from app.services.insights.narratives.source_narratives import source_narrative_report


def cell(address, value, number_format="General"):
    return {
        "address": address,
        "value": value,
        "formula": None,
        "cached_value": None,
        "number_format": number_format,
    }


def region(*rows):
    return {
        "title": None,
        "semantic": {"role": "data"},
        "preview_rows": list(rows),
        "analysis_rows": list(rows),
    }


def report_for(*regions):
    facts = build_business_facts("Sheet1", list(regions), [], max_records=12)
    return source_narrative_report({
        "sheets": [{"name": "Sheet1", "business_facts": facts}],
    })


def test_duplicate_period_end_dates_are_not_described_as_a_date_axis():
    report = report_for(region(
        [cell("B30", "FINANCIAL HIGHLIGHTS")],
        [cell("B31", "METRICS"), cell("C31", "MRQ"), cell("D31", "MRY")],
        [
            cell("B32", "Period Ended"),
            cell("C32", "2024-12-31T00:00:00", "mm-dd-yy"),
            cell("D32", "2024-12-31T00:00:00", "mm-dd-yy"),
        ],
        [
            cell("B33", "Cash and Cash Equivalents"),
            cell("C33", 571_195_000),
            cell("D33", 571_195_000),
        ],
    ))

    rendered = report.model_dump_json()
    assert "2개 날짜" not in rendered
    assert "날짜별 차이" not in rendered


def test_distinct_date_columns_still_describe_school_meals_by_date():
    report = report_for(region(
        [cell("C3", "학교 급식 영양 표시")],
        [
            cell("C5", "일자"),
            cell("H5", "2026-09-01T00:00:00", "yyyy-mm-dd"),
            cell("J5", "2026-09-02T00:00:00", "yyyy-mm-dd"),
        ],
        [
            cell("C6", "중식"),
            cell("H6", "현미밥, 미역국, 배추김치(9)"),
            cell("J6", "보리밥, 된장국(5)"),
        ],
        [cell("C20", "열량(kcal)"), cell("H20", 720), cell("J20", 740)],
    ))

    rendered = report.model_dump_json()
    assert "2개 날짜" in report.overview
    assert "2026년 9월 1일" in rendered
    assert "2026년 9월 2일" in rendered
    assert "현미밥" in rendered and "보리밥" in rendered


def test_adjacent_date_header_and_body_regions_form_one_sparse_table():
    header = region([
        cell("C5", "주간 영양량"), cell("H5", "09월 01일(화)"),
        cell("J5", "09월 02일(수)"),
    ])
    body = region(
        [cell("C6", "중식"), cell("H6", "현미밥, 미역국"),
         cell("J6", "보리밥, 된장국")],
        [cell("C7", "열량(kcal)"), cell("H7", 720), cell("J7", 740)],
    )

    report = report_for(header, body)
    rendered = report.model_dump_json()

    assert "현미밥" in rendered and "보리밥" in rendered
    assert "720" in rendered and "740" in rendered
    assert "2개 날짜" in report.overview


def test_date_cells_from_separate_regions_do_not_form_one_date_axis():
    first = region(
        [cell("A1", "기준일"), cell("B1", "2026-09-01T00:00:00")],
        [cell("A2", "매출"), cell("B2", 100)],
    )
    second = region(
        [cell("D1", "기준일"), cell("E1", "2026-09-02T00:00:00")],
        [cell("D2", "비용"), cell("E2", 200)],
    )

    report = report_for(first, second)
    rendered = report.model_dump_json()
    assert "2개 날짜" not in rendered
    assert "날짜별 차이" not in rendered
    assert not any(
        any("!B" in evidence for evidence in item.evidence)
        and any("!E" in evidence for evidence in item.evidence)
        for item in report.insights
    )


def test_single_column_regions_from_side_by_side_tables_are_not_joined():
    report = report_for(
        region([cell("A1", "기준일")], [cell("A2", "매출")]),
        region([cell("B1", "2026-09-01T00:00:00")], [cell("B2", 100)]),
        region([cell("D1", "기준일")], [cell("D2", "비용")]),
        region([cell("E1", "2026-09-02T00:00:00")], [cell("E2", 200)]),
    )

    rendered = report.model_dump_json()
    assert "2개 날짜" not in rendered
    assert not any(
        any("!B" in evidence for evidence in item.evidence)
        and any("!E" in evidence for evidence in item.evidence)
        for item in report.insights
    )


def test_new_date_header_ends_a_transposed_table_scope():
    report = report_for(
        region([cell("C1", "일자")], [cell("C2", "중식")]),
        region([cell("H1", "2026-09-01")], [cell("H2", "현미밥, 미역국")]),
        region([cell("J1", "2026-09-02")], [cell("J2", "보리밥, 된장국")]),
        region([cell("C10", "일자")], [cell("C11", "석식")]),
        region([cell("H10", "2026-10-01")], [cell("H11", "쌀밥, 콩나물국")]),
        region([cell("J10", "2026-10-02")], [cell("J11", "잡곡밥, 된장국")]),
    )

    first_scope = [item for item in report.insights if "현미밥" in item.fact]
    assert first_scope
    assert all("!H10" not in evidence and "!J10" not in evidence
               for item in first_scope for evidence in item.evidence)
