"""요청이 밝힌 계산으로 새 값을 허용하는 규칙 검증.

값을 잘못 허용하면 원본이 엉뚱하게 바뀌므로, 허용하는 경우보다
허용하지 않아야 하는 경우를 더 많이 확인한다.
"""
from decimal import Decimal

from app.agent.writeback.derived_values import authorize_value, derived_value


def test_applies_a_percent_decrease_to_the_current_value():
    found = derived_value(1081, 973, "서비스 부서 인원을 10% 줄여줘")

    assert found is not None
    assert "10%" in found and "감소" in found and "1081" in found


def test_applies_a_percent_increase_to_the_current_value():
    assert derived_value(200, 230, "예산을 15% 인상해줘") is not None
    assert derived_value(200, 230, "예산을 15퍼센트 올려줘") is not None


def test_allows_either_rounding_of_the_result_but_nothing_further():
    # 1081 × 0.9 = 972.9. 올리든 내리든 한 칸까지는 같은 계산으로 보고,
    # 그 밖은 계산으로 설명되지 않는다.
    assert derived_value(1081, Decimal("972.9"), "10% 줄여줘") is not None
    assert derived_value(1081, 973, "10% 줄여줘") is not None
    assert derived_value(1081, 972, "10% 줄여줘") is not None
    assert derived_value(1081, 971, "10% 줄여줘") is None
    assert derived_value(1081, 974, "10% 줄여줘") is None


def test_applies_an_absolute_increase_or_decrease():
    assert derived_value(1081, 981, "서비스 인원을 100명 줄여줘") is not None
    assert derived_value(1081, 1181, "서비스 인원을 100명 늘려줘") is not None
    assert derived_value(1081, 1081, "서비스 인원을 100명 줄여줘") is None


def test_needs_a_direction_so_a_bare_number_is_not_a_calculation():
    assert derived_value(1081, 981, "서비스 인원 100명 확인해줘") is None
    assert derived_value(200, 230, "15% 항목을 확인해줘") is None


def test_ignores_a_direction_word_that_is_far_from_the_number():
    # 숫자에서 멀리 떨어진 낱말까지 끌어오면 엉뚱한 계산이 만들어진다.
    assert derived_value(1081, 81, "10 때문에 여러 줄을 읽은 다음 결국 줄여줘") is None


def test_does_not_guess_when_the_request_states_the_value_to_change_to():
    # "1081에서 1000으로"는 바꿀 값을 직접 밝힌 요청이라 계산을 추측하지 않는다.
    assert derived_value(1081, 81, "서비스 감소 인원을 1081명에서 1000명으로 줄여줘") is None
    assert derived_value(1081, 81, "1081 → 1000 으로 줄여줘") is None


def test_a_column_named_like_a_direction_does_not_become_a_calculation():
    assert derived_value(1081, 1000, "서비스 부서의 감소 인원을 확인해줘") is None


def test_ignores_non_numeric_cells():
    assert derived_value("서비스", 900, "10% 줄여줘") is None
    assert derived_value(1081, "천명", "10% 줄여줘") is None
    assert derived_value(None, 900, "10% 줄여줘") is None


def test_a_value_written_in_the_request_needs_no_calculation():
    derivation, rejection = authorize_value(1081, 1000, "1081명을 1000명으로", None)

    assert derivation is None and rejection is None


def test_a_calculated_value_is_allowed_and_explains_itself():
    derivation, rejection = authorize_value(1081, 973, "10% 줄여줘", None)

    assert rejection is None
    assert derivation is not None and "1081" in derivation


def test_a_value_with_neither_a_literal_nor_a_calculation_is_rejected():
    derivation, rejection = authorize_value(1081, 777, "적당히 줄여줘", None)

    assert derivation is None
    assert rejection is not None and "계산 방법" in rejection


def test_a_formula_change_skips_the_value_rule():
    derivation, rejection = authorize_value(1081, "=SUM(A1:A9)", "=SUM(A1:A9) 넣어줘", "=SUM(A1:A9)")

    assert derivation is None and rejection is None


def test_applies_a_multiple_or_a_half():
    assert derived_value(1081, 2162, "서비스 인원을 두 배로 늘려줘") is not None
    assert derived_value(1081, 3243, "3배로 늘려줘") is not None
    assert derived_value(1081, 541, "서비스 인원을 절반으로 줄여줘") is not None
    assert derived_value(1081, 540, "서비스 인원을 반으로 줄여줘") is not None
    assert derived_value(1081, 500, "서비스 인원을 절반으로 줄여줘") is None


def test_a_word_that_merely_contains_the_multiple_syllable_is_not_a_calculation():
    assert derived_value(1081, 2162, "2배정된 인원을 확인해줘") is None
    assert derived_value(1081, 2162, "인원을 배분해줘") is None
