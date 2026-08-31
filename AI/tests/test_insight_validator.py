from app.services.insights.models import WorkbookInsight, WorkbookInsightReport
from app.services.insights.validator import validate_workbook_insights


def report(
    evidence: str = "Sales!A1:B2",
    fact: str = "Sales 값은 100에서 80으로 20 감소했습니다.",
    cause: str | None = None,
) -> WorkbookInsightReport:
    return WorkbookInsightReport(
        overview="Sales 변화 요약",
        insights=[
            WorkbookInsight(
                title="매출 변화",
                fact=fact,
                cause=cause,
                impact="최신 값 80을 기준으로 판단해야 합니다.",
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


def test_keeps_insight_with_unmatched_reference_for_user_review() -> None:
    result = validate_workbook_insights(report(evidence="Sales!Z99"), context())

    assert len(result.insights) == 1
    assert result.validation.limited_count == 1
    assert result.validation.blocked_count == 0
    assert result.insights[0].validation_status == "limited"


def test_marks_multiple_citations_as_limited_when_one_is_unmatched() -> None:
    result = validate_workbook_insights(
        report(evidence="Sales!A1:B2, Fake!Z99"), context()
    )

    assert result.validation.limited_count == 1


def test_keeps_unmatched_numeric_claim_for_user_review() -> None:
    result = validate_workbook_insights(
        report(fact="Sales 값이 근거에 없는 999로 변경됐습니다."), context()
    )

    assert result.validation.limited_count == 1
    assert result.insights[0].fact.endswith("999로 변경됐습니다.")


def test_blocks_only_insight_without_required_content() -> None:
    result = validate_workbook_insights(report(fact=""), context())

    assert result.insights == []
    assert result.validation.blocked_count == 1


def test_removes_cause_without_direct_formula_or_metadata_evidence() -> None:
    result = validate_workbook_insights(
        report(cause="담당자 변경 때문에 감소했습니다."), context()
    )

    insight = result.insights[0]
    assert insight.cause is None
    assert insight.validation_status == "limited"
    assert insight.confidence == 0.79
