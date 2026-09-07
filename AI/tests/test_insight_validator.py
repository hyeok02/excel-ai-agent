from app.services.insights.models import WorkbookInsight, WorkbookInsightReport
from app.services.insights.validator import validate_workbook_insights


def report(
    evidence: str = "Sales!A1:B2",
    fact: str = "Sales 값은 100에서 80으로 20 감소했습니다.",
    cause: str | None = None,
    impact: str = "최신 값 80을 기준으로 판단해야 합니다.",
) -> WorkbookInsightReport:
    return WorkbookInsightReport(
        overview="Sales 변화 요약",
        insights=[
            WorkbookInsight(
                title="매출 변화",
                fact=fact,
                cause=cause,
                impact=impact,
                category="summary",
                severity="info",
                evidence=[evidence],
                confidence=0.95,
            )
        ],
    )


def context() -> dict[str, object]:
    return {
        "omitted_sheet_count": 0,
        "sheets": [
            {
                "name": "Sales",
                "business_facts": {
                    "numeric_changes": [
                        {
                            "earliest_value": 100,
                            "latest_value": 80,
                            "change": -20,
                            "evidence": ["Sales!A1:B2"],
                        }
                    ]
                },
                "formula_samples": [
                    {"cell": "D2", "formula": "=SUM(A2:B2)"}
                ],
            }
        ],
    }


def test_keeps_insight_when_reference_and_numeric_claims_are_grounded() -> None:
    result = validate_workbook_insights(report(), context())

    assert result.validation.verified_count == 1
    assert result.validation.blocked_count == 0
    assert result.insights[0].validation_status == "verified"


def test_blocks_insight_with_unmatched_reference() -> None:
    result = validate_workbook_insights(report(evidence="Sales!Z99"), context())

    assert result.validation.blocked_count == 1
    assert all("Sales!Z99" not in item.evidence for item in result.insights)
    assert report().insights[0].fact not in result.overview


def test_blocks_multiple_citations_when_one_is_unmatched() -> None:
    result = validate_workbook_insights(
        report(evidence="Sales!A1:B2, Fake!Z99"), context()
    )

    assert result.validation.blocked_count == 1
    assert report().insights[0].fact not in result.overview
    assert all("Fake!Z99" not in " ".join(item.evidence) for item in result.insights)


def test_blocks_unmatched_numeric_claim() -> None:
    result = validate_workbook_insights(
        report(fact="Sales 값이 근거에 없는 999로 변경됐습니다."), context()
    )

    assert result.validation.blocked_count == 1
    assert "999" not in result.overview
    assert all("999" not in item.fact for item in result.insights)


def test_verifies_dates_and_rounded_change_rate_numerically() -> None:
    trend_context = context()
    trend_context["sheets"][0]["business_facts"]["selected_records"] = [
        {"location": "Sales!A1", "values": [{"cell": "A1", "value": "인원(명)"}]}
    ]
    trend_context["sheets"][0]["business_facts"]["numeric_changes"] = [
        {
            "earliest_period": "2023-09-30",
            "earliest_value": 6101,
            "latest_period": "2025-06-30",
            "latest_value": 5417,
            "change": -684,
            "change_rate_percent": -11.21,
            "evidence": ["Sales!A1:B2"],
        }
    ]
    result = validate_workbook_insights(
        report(
            fact=(
                "2023년 9월 6,101명에서 2025년 6월 5,417명으로 "
                "684명, 11.2% 감소했습니다."
            ),
            impact="최신 값 5,417명을 기준으로 판단해야 합니다.",
        ),
        trend_context,
    )

    insight = result.insights[0]
    assert result.validation.blocked_count == 0
    assert insight.validation_status == "verified"
    assert insight.confidence == 0.95


def test_blocks_only_insight_without_required_content() -> None:
    result = validate_workbook_insights(report(fact=""), context())

    assert result.insights == []
    assert result.validation.blocked_count == 1


def test_removes_cause_without_direct_formula_or_metadata_evidence() -> None:
    result = validate_workbook_insights(
        report(cause="담당자 변경 때문에 감소했습니다."), context()
    )

    insight = result.insights[0]
    assert result.validation.blocked_count == 0
    assert insight.fact == report().insights[0].fact
    assert insight.cause is None
    assert insight.validation_status == "limited"
    assert insight.confidence == 0.95
