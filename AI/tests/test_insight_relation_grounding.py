"""Source relations remain intact across layouts, broad citations and signs."""
import pytest

from app.services.insights.verification.validator import validate_workbook_insights
from tests.test_insight_grounding_regression import candidate


def context(cells, records=None):
    return {"sheets": [{"name": "Sheet1", "business_facts": {
        "selected_records": records or [{"location": "Sheet1!A1:D5", "values": [
            {"cell": address, "value": value} for address, value in cells
        ]}],
    }}]}


def verify(fact, source):
    return validate_workbook_insights(candidate(fact, title="원본 내용",
                                               evidence=["Sheet1!A1:D5"]), source)


@pytest.mark.parametrize("cells", [
    [("A1", "항목"), ("B1", "실적"), ("A2", "매출"), ("B2", 100),
     ("A3", "비용"), ("B3", 50)],
    [("A2", "매출"), ("B2", 100), ("C2", "비용"), ("D2", 50)],
    [("A1", "매출"), ("B1", "비용"), ("A2", 100), ("B2", 50)],
])
@pytest.mark.parametrize(("fact", "valid"), [
    ("매출은 50입니다.", False), ("비용은 100입니다.", False),
    ("매출은 100입니다.", True), ("비용은 50입니다.", True),
    ("매출은 100이고 비용은 50입니다.", True),
    ("매출은 50이고 비용은 100입니다.", False),
])
def test_metric_binding_is_not_a_bag_of_cited_values(cells, fact, valid):
    result = verify(fact, context(cells))
    assert (result.validation.blocked_count == 0) is valid
    assert any(item.fact == fact for item in result.insights) is valid


@pytest.mark.parametrize(("fact", "valid"), [
    ("손익은 -100입니다.", True), ("손익은 100입니다.", False),
    ("예산은 100입니다.", True), ("예산은 -100입니다.", False),
])
def test_signed_values_do_not_borrow_the_other_cells_sign(fact, valid):
    result = verify(fact, context([("A2", "손익"), ("B2", -100),
                                   ("A3", "예산"), ("B3", 100)]))
    assert (result.validation.blocked_count == 0) is valid


@pytest.mark.parametrize(("fact", "valid"), [
    ("서울 매출은 100입니다.", True), ("서울 매출은 50입니다.", False),
    ("부산 매출은 50입니다.", True), ("부산 매출은 100입니다.", False),
])
def test_row_qualifiers_are_bound_to_the_same_observation(fact, valid):
    source = context([], records=[{
        "location": f"Sheet1!A{row}:B{row}", "values": [
            {"cell": f"A{row}", "value": place},
            {"cell": f"B{row}", "label": "매출", "value": amount},
        ],
    } for row, place, amount in ((2, "서울", 100), (3, "부산", 50))])
    result = verify(fact, source)
    assert (result.validation.blocked_count == 0) is valid


def test_model_overview_cannot_smuggle_a_wrong_binding():
    source = context([("A2", "매출"), ("B2", 100), ("A3", "비용"), ("B3", 50)])
    report = candidate("매출은 100입니다.", evidence=["Sheet1!A1:D5"])
    report.overview = "이 파일은 매출은 50입니다 관련 자료입니다."
    result = validate_workbook_insights(report, source)
    assert "매출은 50" not in result.overview


def test_valid_fact_does_not_carry_swapped_auxiliary_claims():
    source = context([("A2", "매출"), ("B2", 100), ("A3", "비용"), ("B3", 50)])
    report = candidate("매출은 100입니다.", title="매출은 50입니다.",
                       impact="비용은 100입니다.", recommendation="매출은 50입니다.",
                       evidence=["Sheet1!A1:D5"])
    result = validate_workbook_insights(report, source)
    assert result.validation.blocked_count == 0
    assert all(item.impact is None and item.recommendation is None for item in result.insights)
    assert "매출은 50" not in result.model_dump_json()
