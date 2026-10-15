import pytest

from tests.support.semantic_claim_fixtures import answer, evidence, grid, observation


def test_symbol_is_rendered_literally_not_as_model_authored_status():
    result = answer(grid(), [observation()], text="장비-A 네트워크는 정상이며 안정적입니다.")
    assert result.status == "limited"
    assert "‘x’" in result.answer and "‘장비-A’" in result.answer
    assert "정상" not in result.answer and "안정적" not in result.answer
    assert result.verification.level == "source_checked"
    assert "claim_semantics" in result.verification.checks


@pytest.mark.parametrize("binding", [
    {"subject_reference": "Data!A3"}, {"period_reference": "Data!C3"},
    {"property_reference": "Data!C1"}, {"value_reference": "Data!B2:B3"},
    {"value_reference": "Data!B99"}, {"fact": "안정적입니다."},
])
def test_invalid_entity_period_property_and_ranges_do_not_get_a_badge(binding):
    result = answer(grid(), [observation(**binding)])
    assert result.status == "insufficient_evidence"
    assert result.verification.level == "unverified"


def test_observation_does_not_replace_a_requested_entity():
    result = answer(grid(), [observation()], question="장비-B의 네트워크 안정 값은?")
    assert result.status == "insufficient_evidence"


@pytest.mark.parametrize("question", ["Data!B3 값은?", "2025년 네트워크 안정 값은?"])
def test_observation_honors_requested_source_and_period(question):
    result = answer(grid(), [observation()], question=question)
    assert result.status == "insufficient_evidence"


def test_observation_cannot_substitute_an_unrelated_column():
    cells = [*grid(), evidence("D2", 100, "매출")]
    result = answer(cells, [observation(value_reference="Data!D2", property_reference=None)],
                    question="네트워크 안정 값은?")
    assert result.status == "insufficient_evidence"


def test_valid_fact_survives_unknown_meaning_and_invalid_second_claim():
    result = answer(grid(), [observation(), {"kind": "unknown"}, observation(subject_reference="Data!A3")])
    assert result.status == "limited"
    assert "‘x’" in result.answer
    assert any("의미, 원인이나 관계" in item for item in result.limitations)
    assert any("제외" in item for item in result.limitations)


def test_joint_header_does_not_establish_identical_business_operations():
    cells = [evidence("E5", "설치,검수 작업")]
    result = answer(cells, [{"kind": "cell_value", "value_reference": "Data!E5"}, {"kind": "unknown"}],
                    question="설치와 검수 작업이 같은 작업이야?", text="설치와 검수는 같은 작업입니다.")
    assert result.status == "limited" and "‘설치,검수 작업’" in result.answer
    assert "같은 작업입니다" not in result.answer
    assert any("관계" in item for item in result.limitations)


def test_unknown_alone_is_not_verified_and_arbitrary_limitations_are_not_displayed():
    result = answer(grid(), [{"kind": "unknown"}], limitations=["네트워크가 실패한 원인은 장비 노후입니다."])
    assert result.verification.level == "unverified"
    assert "노후" not in " ".join(result.limitations)


def test_missing_external_formula_result_is_not_rendered_as_blank_or_zero():
    cells = [evidence("B2", None, "Revenue", formula="=EXTERNAL_DATA()")]
    result = answer(cells, [{"kind": "cell_value", "value_reference": "Data!B2"}], question="Revenue 값은?")
    assert result.status == "insufficient_evidence"


def test_symbols_booleans_and_negation_in_values_are_preserved_verbatim():
    for value in ("not completed", "미완료", False, "△"):
        result = answer([evidence("B2", value, "상태")],
                        [{"kind": "cell_value", "value_reference": "Data!B2"}], question="상태 값은?")
        assert str(value) in result.answer
        assert result.status == "limited"
