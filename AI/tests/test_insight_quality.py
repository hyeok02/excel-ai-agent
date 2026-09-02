from app.services.insights.models import WorkbookInsight, WorkbookInsightReport
from app.services.insights.quality import ensure_business_report


def _generic_report() -> WorkbookInsightReport:
    return WorkbookInsightReport(
        overview="이 파일은 기업 인력 정보를 담고 있습니다.",
        insights=[
            WorkbookInsight(
                title="시트 내용",
                fact="이 시트에는 직원 수 관련 항목이 포함되어 있습니다.",
                cause=None,
                impact="직원 수 관련 지표를 확인할 수 있습니다.",
                category="structure",
                severity="info",
                evidence=["인력 시트"],
                confidence=0.5,
            )
        ],
    )


def test_replaces_generic_report_with_concrete_business_change() -> None:
    context = {
        "sheets": [
            {
                "business_facts": {
                    "selected_records": [
                        {
                            "values": [
                                {"value": "Focus Co. ►"},
                                {"value": "Riot Games, Inc."},
                            ]
                        }
                    ],
                    "numeric_changes": [
                        {
                            "metric": "Total Employees",
                            "earliest_period": "2023-09-01T00:00:00",
                            "earliest_value": 6101,
                            "latest_period": "2025-06-01T00:00:00",
                            "latest_value": 5417,
                            "change": -684,
                            "change_rate_percent": -11.21,
                            "evidence": ["인력!E115:L115", "인력!E108:L108"],
                        }
                    ],
                }
            }
        ]
    }

    result = ensure_business_report(_generic_report(), context)

    assert "Riot Games, Inc." in result.overview
    assert "6,101" in result.overview
    assert "5,417" in result.overview
    assert result.insights[0].evidence == ["인력!E115:L115", "인력!E108:L108"]


def test_keeps_concrete_llm_report() -> None:
    report = WorkbookInsightReport(
        overview="Riot Games 직원 수는 6,101명에서 5,417명으로 감소했습니다.",
        insights=[
            WorkbookInsight(
                title="직원 수 감소",
                fact="2023년 대비 2025년 직원 수가 684명 감소했습니다.",
                cause=None,
                impact="최신 인력 규모가 이전보다 작습니다.",
                category="summary",
                severity="info",
                evidence=["인력!E108:L115"],
                confidence=0.98,
            )
        ],
    )
    context = {"sheets": [{"business_facts": {"numeric_changes": [{}]}}]}

    assert ensure_business_report(report, context) is report


def test_builds_concrete_report_for_a_workbook_from_another_domain() -> None:
    """인사 워크북 전용 컬럼명 없이도 같은 규칙으로 동작해야 한다."""
    context = {
        "sheets": [
            {
                "business_facts": {
                    "selected_records": [
                        {
                            "values": [
                                {"value": "설비 라인"},
                                {"value": "2공장 압출 라인"},
                            ]
                        }
                    ],
                    "numeric_changes": [
                        {
                            "metric": "월간 불량률",
                            "earliest_period": "2025-01-01T00:00:00",
                            "earliest_value": 2.4,
                            "latest_period": "2025-06-01T00:00:00",
                            "latest_value": 3.6,
                            "change": 1.2,
                            "change_rate_percent": 50.0,
                            "evidence": ["품질!C4:H4"],
                        }
                    ],
                }
            }
        ]
    }

    result = ensure_business_report(_generic_report(), context)

    assert "2공장 압출 라인" in result.overview
    assert "월간 불량률" in result.overview
    assert result.insights[0].evidence == ["품질!C4:H4"]
