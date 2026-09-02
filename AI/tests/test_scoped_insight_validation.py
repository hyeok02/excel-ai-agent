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
            fact="회사는 580만 달러 규모의 투자를 유치했습니다.",
            impact="투자 내역을 원본 거래 기록에서 확인할 수 있습니다.",
        ),
        transaction_context,
    )

    assert result.insights[0].validation_status == "verified"


def test_does_not_use_a_number_from_an_unrelated_reference() -> None:
    scoped_context = context()
    scoped_context["sheets"][0]["business_facts"]["selected_records"] = [
        {
            "location": "Sales!C1:C2",
            "values": [{"cell": "C1", "value": 999}],
        }
    ]

    result = validate_workbook_insights(
        report(evidence="Sales!A1:B2", fact="Sales 값은 999입니다."), scoped_context
    )

    assert result.insights[0].validation_status == "limited"


def test_removes_speculative_review_point_without_blocking_fact() -> None:
    result = validate_workbook_insights(
        report(impact="인력 감소는 외부 위탁 가능성을 시사합니다."), context()
    )

    assert result.insights[0].validation_status == "verified"
    assert result.insights[0].impact is None


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
            fact="2025년 3월 11일 580만 달러 투자가 기록됐습니다.",
        ),
        transaction_context,
    )

    assert result.insights[0].validation_status == "verified"


def test_wrong_adjacent_range_cannot_borrow_missing_cell_value() -> None:
    peer_context = context()
    peer_context["sheets"][0]["business_facts"]["selected_records"] = [
        {
            "location": "Sales!C26:I26",
            "values": [
                {"cell": "H26", "value": 5411},
                {"cell": "I26", "value": 3.67},
            ],
        }
    ]

    result = validate_workbook_insights(
        report(
            evidence="Sales!I26:J26",
            fact="직원 수는 5,411명이고 평균 근속연수는 3.67년입니다.",
        ),
        peer_context,
    )

    assert result.insights[0].validation_status == "limited"


def test_keeps_review_point_anchored_to_a_cited_number() -> None:
    anchored = "최신 값 80을 기준으로 후속 비교를 맞춰야 합니다."

    result = validate_workbook_insights(report(impact=anchored), context())

    assert result.insights[0].impact == anchored


def test_removes_review_point_that_leaves_the_workbook_in_any_domain() -> None:
    """업종별 표현 목록이 아니라 근거 연결 여부로 판단하는지 확인한다."""
    result = validate_workbook_insights(
        report(impact="설비 노후화로 공정 재편이 필요할 수 있습니다."), context()
    )

    assert result.insights[0].impact is None
    assert result.insights[0].validation_status == "verified"


def test_treats_digits_inside_a_workbook_name_as_part_of_the_name() -> None:
    """'2공장'의 2를 근거 없는 수치로 오해하면 정상 문장이 통째로 버려진다."""
    plant_context = context()
    plant_context["sheets"][0]["business_facts"]["selected_records"] = [
        {
            "location": "Sales!A1:B2",
            "values": [{"cell": "A1", "value": "2공장 압출 라인"}],
        }
    ]

    result = validate_workbook_insights(
        report(
            fact="2공장 압출 라인의 값은 100에서 80으로 20 감소했습니다.",
            impact="2공장 압출 라인의 최근 값을 함께 확인해야 합니다.",
        ),
        plant_context,
    )

    insight = result.insights[0]
    assert insight.validation_status == "verified"
    assert insight.impact is not None


def test_still_flags_a_number_that_is_not_a_workbook_name() -> None:
    result = validate_workbook_insights(
        report(fact="Sales 값이 987654로 늘었습니다."), context()
    )

    assert result.insights[0].validation_status == "limited"
