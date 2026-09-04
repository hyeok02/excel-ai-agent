import pytest

from app.services.insights.derived_claim_grounding import grounded_derivation


REFERENCES = {"sheet1!a2:c2"}
SOURCES = ["생산량", "100", "80", "20", "2023-09", "2025-06"]
CHANGE = {
    "metric": "생산량", "earliest_value": 100, "latest_value": 80, "change": -20,
    "change_rate_percent": -20, "evidence": ["Sheet1!A2:C2"],
}


def supports(text, sources=None, changes=None, references=None):
    return grounded_derivation(
        text, SOURCES if sources is None else sources,
        REFERENCES if references is None else references,
        [CHANGE] if changes is None else changes,
    )


@pytest.mark.parametrize("text", [
    "평균 생산량은 80입니다.", "생산량 합계는 100입니다.",
    "최대 생산량은 80입니다.", "최소 생산량은 100입니다.",
    "Average is 80.", "The total is 100.",
])
def test_does_not_invent_statistics_from_coincident_source_numbers(text):
    assert not supports(text)


@pytest.mark.parametrize(("label", "text"), [
    ("평균 생산량", "평균 생산량은 80입니다."),
    ("합계", "생산량 합계는 100입니다."),
    ("=MAX(A2:A4)", "최대 생산량은 100입니다."),
    ("=MIN(A2:A4)", "최소 생산량은 80입니다."),
])
def test_accepts_statistics_explicitly_labeled_or_computed_in_source(label, text):
    assert supports(text, sources=[*SOURCES, label])


def test_rejects_the_wrong_change_direction():
    assert not supports("생산량은 100에서 80으로 20 증가했습니다.")
    assert supports("생산량은 100에서 80으로 20 감소했습니다.")


def test_rejects_swapped_endpoints_even_if_direction_word_is_correct():
    assert not supports("생산량은 80에서 100으로 20 감소했습니다.")


def test_supports_canonical_dated_numeric_change_format():
    assert supports("생산량 지표는 2023년 09월 100에서 2025년 06월 80로 20(20%) 감소했습니다.")


def test_requires_change_evidence_in_the_cited_range():
    assert not supports("생산량은 20 감소했습니다.", references={"sheet1!d2:f2"})
    assert not supports("생산량은 20 감소했습니다.", changes=[])


def test_requires_all_evidence_ranges_not_just_one_of_them():
    assert not supports("생산량은 20 감소했습니다.", changes=[{
        **CHANGE, "evidence": ["Sheet1!A2:C2", "Other!A2:C2"],
    }])


def test_source_quotes_can_report_instructions_without_claiming_computation():
    source = "주간 평균은 5일의 값을 합산하여 계산합니다."
    assert supports(f'원본 내용: "{source}"', sources=[source], changes=[])
    assert supports(source, sources=[source], changes=[])


def test_quote_of_one_number_cannot_validate_unquoted_computation():
    assert not supports('평균 생산량은 "80"입니다.', sources=["생산량", "80"])


def test_fabricated_quote_is_not_a_source_quote_exemption():
    assert not supports('원본 내용: "평균 생산량은 80입니다."')


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), True, "invalid"])
def test_invalid_change_records_never_validate_a_numeric_direction(bad):
    assert not supports("생산량은 20 감소했습니다.", changes=[{**CHANGE, "change": bad}])


def test_inconsistent_computed_delta_is_rejected():
    assert not supports("생산량은 20 증가했습니다.", changes=[{**CHANGE, "change": 20}])


def test_increase_from_negative_values_preserves_endpoint_signs():
    change = {**CHANGE, "earliest_value": -100, "latest_value": -80, "change": 20}
    assert supports("값은 -100에서 -80으로 20 증가했습니다.", changes=[change])
    assert not supports("값은 100에서 80으로 20 증가했습니다.", changes=[change])
