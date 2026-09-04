from app.services.insights.validator import validate_workbook_insights
from tests.test_insight_validator import context, report


def test_verifies_equivalent_korean_and_english_magnitude_units() -> None:
    transaction_context = context()
    transaction_context["sheets"][0]["business_facts"]["selected_records"] = [
        {
            "location": "Sales!A1:B2",
            "values": [
                {
                    "cell": "A1",
                    "value": "The company received $5.8 million in funding.",
                }
            ],
        }
    ]
    result = validate_workbook_insights(
        report(
            fact="Sales 값은 580만입니다.",
            impact="Sales 값을 원본에서 확인하세요.",
        ),
        transaction_context,
    )

    assert result.validation.blocked_count == 0
    assert result.insights[0].validation_status == "verified"
    assert result.insights[0].fact == "Sales 값은 580만입니다."


def test_verifies_reasonable_range_covering_selected_source_rows() -> None:
    transaction_context = context()
    transaction_context["sheets"][0]["business_facts"]["selected_records"] = [
        {
            "location": "Sales!J69:M69",
            "values": [
                {"cell": "J69", "value": "2025-03-11"},
                {"cell": "M69", "value": "$5.8 million funding"},
            ],
        }
    ]

    result = validate_workbook_insights(
        report(
            evidence="Sales!J65:M75",
            fact="Sales 값은 2025년 3월 11일 580만으로 기록됐습니다.",
        ),
        transaction_context,
    )

    assert result.validation.blocked_count == 0
    assert result.insights[0].validation_status == "verified"
    assert result.insights[0].fact == "Sales 값은 2025년 3월 11일 580만으로 기록됐습니다."
