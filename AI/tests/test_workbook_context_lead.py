from app.services.insights.comparable_narratives import comparable_transaction_report
from app.services.insights.models import WorkbookInsight, WorkbookInsightReport
from app.services.insights.trend_narratives import trend_report
from app.services.insights.validator import validate_workbook_insights
from tests.support.narrative_contexts import trend_context


def test_trend_overview_starts_with_what_the_file_is_about():
    items, overview = trend_report(trend_context())
    draft = WorkbookInsightReport(overview=overview, insights=items)

    result = validate_workbook_insights(draft, trend_context())

    assert result.overview.startswith("이 파일은 푸른연구원의 전체 인원 변동을 다룹니다.")
    assert items[0].fact.startswith("푸른연구원의 전체 인원")


def test_comparison_overview_starts_with_its_subject_and_analysis_type():
    context = {"sheets": [{"name": "Deal Review", "business_facts": {
        "comparable_transactions": {
            "subject": "Sample Investment Co.",
            "metrics": [{
                "kind": "transaction_value", "label": "Total Value ($M)",
                "subject_value": 80.0, "median": 100.0, "difference": -20.0,
                "difference_percent": -20.0, "valid_count": 5, "peer_count": 5,
                "evidence": ["'Deal Review'!A1:B6"],
            }],
        }
    }}]}

    items, overview = comparable_transaction_report(context)
    draft = WorkbookInsightReport(overview=overview, insights=items)

    result = validate_workbook_insights(draft, context)

    assert result.overview.startswith(
        "이 파일은 Sample Investment Co. 거래가격을 비슷한 거래들과 비교한 자료입니다."
    )
    assert "전체 거래가격은 비슷한 거래들의 중간 수준보다 20.0% 낮았습니다" in overview
    assert items[0].fact.startswith("Sample Investment Co.의 총 거래가치는")


def test_generic_report_gets_a_source_anchored_file_context_sentence():
    context = {"sheets": [{"name": "Events", "business_facts": {
        "selected_records": [{
            "location": "Events!A2:C2",
            "values": [
                {"cell": "A2", "value": "2025-12-11T00:00:00"},
                {"cell": "B2", "value": "Conference"},
                {"cell": "C2", "value": "Sample Co. presents at Consumer Conference"},
            ],
        }],
    }}]}
    fact = "2025년 12월 11일에 ‘Sample Co. presents at Consumer Conference’가 기록되어 있습니다."
    draft = WorkbookInsightReport(
        overview=("이 파일은 Conference로 분류된 기업 행사를 날짜별로 정리한 자료입니다. "
                  + fact),
        insights=[WorkbookInsight(
            title="Conference", fact=fact, category="summary", severity="info",
            evidence=["Events!A2:C2"], confidence=1,
        )],
    )

    result = validate_workbook_insights(draft, context)

    assert result.overview.startswith(
        "이 파일은 주요 사건과 관련 내용을 날짜별로 정리한 자료입니다."
    )


def test_generic_context_rejects_a_name_missing_from_the_source():
    context = trend_context()
    items, _ = trend_report(context)
    draft = WorkbookInsightReport(
        overview="이 파일은 Fabricated Corp.의 직원 변동을 다룹니다.",
        insights=items,
    )

    result = validate_workbook_insights(draft, context)

    assert "Fabricated Corp." not in result.overview
    assert result.overview.startswith("이 파일은 푸른연구원의 전체 인원 변동을 다룹니다.")
