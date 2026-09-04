from app.services.insights.models import WorkbookInsightReport
from app.services.insights.quality import build_source_report, ensure_business_report


def _context(rows: list[list[tuple[str, object]]]) -> dict[str, object]:
    return {"sheets": [{"name": "급식", "business_facts": {
        "selected_records": [
            {"values": [{"cell": cell, "value": value} for cell, value in row]}
            for row in rows
        ], "numeric_changes": [],
    }}]}


def test_fallback_quotes_nutrient_values_and_menu_without_new_claims() -> None:
    context = _context([
        [("C20", "단백질(g)"), ("H20", 25.7), ("J20", 27.1)],
        [("H6", "현미밥, 미역국, 배추김치(9)"), ("J6", "잡곡밥, 된장국(5)")],
    ])

    report = build_source_report(context)

    assert len(report.insights) == 2
    assert report.insights[0].title == "단백질(g)"
    assert "25.7" in report.insights[0].fact
    assert "27.1" in report.insights[0].fact
    assert report.insights[0].evidence == ["'급식'!C20", "'급식'!H20", "'급식'!J20"]
    assert "배추김치(9)" in report.insights[1].fact
    assert "감소" not in report.overview
    for insight in report.insights:
        assert insight.cause is None
        assert insight.impact is None
        assert insight.recommendation is None


def test_fallback_keeps_origins_and_does_not_guess_units_or_roles() -> None:
    report = build_source_report(_context([
        [("C8", "쇠고기(종류)/가공품"), ("H8", "국내산(한우)/"), ("J8", "국내산")],
    ]))

    assert len(report.insights) == 1
    assert "쇠고기(종류)/가공품" in report.insights[0].fact
    assert "국내산(한우)/" in report.insights[0].fact
    assert "Riot" not in report.overview
    assert "인력" not in report.overview


def test_empty_or_unlabelled_numeric_context_stays_empty() -> None:
    assert build_source_report({"sheets": []}).insights == []
    report = build_source_report(_context([[("A1", 3), ("B1", 9)]]))
    assert report.insights == []


def test_empty_llm_draft_uses_literal_source_not_a_canned_example() -> None:
    draft = WorkbookInsightReport(overview="", insights=[], limitations=[])

    report = ensure_business_report(draft, _context([
        [("C12", "쌀"), ("H12", "국내산"), ("J12", "국내산")],
    ]))

    assert len(report.insights) == 1
    assert report.insights[0].title == "쌀"
    assert "6,101" not in report.overview


def test_fallback_limits_cards_and_excludes_nonfinite_or_invalid_cells() -> None:
    context = _context([
        [("A1", "항목"), ("B1", 0)],
        [("A2", "항목"), ("B2", float("nan")), ("B0", 12)],
        [("A3", "항목"), ("B3", 2)],
    ])

    report = build_source_report(context, max_insights=1)

    assert len(report.insights) == 1
    assert "‘0’" in report.overview
    assert build_source_report(context, max_insights=0).insights == []


def test_incomplete_numeric_change_uses_source_rows_without_guessing_missing_fields() -> None:
    context = _context([[("A1", "합계"), ("B1", 7)]])
    context["sheets"][0]["business_facts"]["numeric_changes"] = [{
        "earliest_value": 3,
        "latest_value": 7,
        "change": 4,
        "evidence": ["급식!B1"],
    }]

    report = build_source_report(context)

    assert report.insights[0].title == "합계"
    assert "‘7’" in report.insights[0].fact
    assert "증가" not in report.overview


def test_source_quotes_are_still_checked_by_the_shared_evidence_validator() -> None:
    from app.services.insights.validator import validate_workbook_insights

    context = _context([
        [("C20", "단백질(g)"), ("H20", 25.7), ("J20", 27.1)],
        [("H6", "현미밥, 미역국, 배추김치(9)"), ("J6", "잡곡밥, 된장국(5)")],
    ])

    report = validate_workbook_insights(build_source_report(context), context)

    assert report.validation.verified_count == 2
    assert report.insights[0].title == "단백질(g)"
    assert report.insights[0].evidence == ["'급식'!C20", "'급식'!H20", "'급식'!J20"]
