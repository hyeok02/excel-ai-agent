"""요청이 밝힌 금액 단위(억/만/천)를 그대로 읽는지 검증한다."""
from app.agent.writeback.derived_values import authorize_value
from app.agent.writeback.value_authorization import value_is_authorized


def _allows(current, new_value, instruction):
    _, reason = authorize_value(current, new_value, instruction, None)
    return reason is None


def test_reads_the_magnitude_the_request_wrote() -> None:
    assert _allows(500_000_000, 400_000_000, "마케팅 예산을 1억 줄여줘")
    assert _allows(1_000_000, 900_000, "10만 줄여줘")
    assert _allows(5_000, 7_000, "2천 늘려줘")


def test_rejects_the_value_that_drops_the_magnitude() -> None:
    """단위를 빼고 읽으면 1원만 깎은 값이 계산 근거까지 달고 승인 화면에 오른다."""
    assert not _allows(500_000_000, 499_999_999, "마케팅 예산을 1억 줄여줘")
    assert not _allows(1_000_000, 999_990, "10만 줄여줘")


def test_explains_the_arithmetic_with_the_scaled_amount() -> None:
    derivation, _ = authorize_value(
        500_000_000, 400_000_000, "마케팅 예산을 1억 줄여줘", None
    )

    assert "100000000" in derivation and "400000000" in derivation


def test_keeps_manteum_as_a_plain_amount() -> None:
    """'10만큼'의 만은 단위가 아니라 조사다."""
    assert _allows(5_000, 4_990, "10만큼 줄여줘")
    assert not _allows(5_000, -95_000, "10만큼 줄여줘")


def test_a_change_amount_is_not_a_target_value() -> None:
    """'1억 줄여줘'의 1억을 목표값으로 받으면 5억이 1억으로 덮어써진다."""
    assert not value_is_authorized(100_000_000, "마케팅 예산을 1억 줄여줘")
    assert not _allows(500_000_000, 100_000_000, "마케팅 예산을 1억 줄여줘")


def test_a_stated_target_still_counts_even_with_a_direction_word() -> None:
    assert value_is_authorized(1000, "B2를 1081에서 1000으로 줄여줘")
    assert _allows(1081, 1000, "B2를 1081에서 1000으로 줄여줘")
    assert _allows(1081, 1000, "B2를 1000으로 바꿔줘")


def test_understands_the_everyday_words_for_up_and_down() -> None:
    for instruction in ("10% 낮춰줘", "10% 깎아줘", "10% 축소해줘", "10% 감액해줘"):
        assert _allows(1000, 900, instruction), instruction
    for instruction in ("10% 높여줘", "10% 확대해줘", "10% 증액해줘"):
        assert _allows(1000, 1100, instruction), instruction


def test_keeps_the_words_that_already_worked() -> None:
    assert _allows(1000, 900, "10% 내려줘")
    assert _allows(1000, 2000, "두 배로 해줘")
    assert _allows(1000, 500, "절반으로 줄여줘")
