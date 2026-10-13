"""반올림 허용 오차가 배율을 따라가는지 — 7%인 원본이 8%를 뒷받침하면 안 된다."""
from app.services.insights.verification.numeric_validation import (
    numbers,
    unmatched_numbers,
)


def grounded(source: str, claim: str) -> bool:
    return not unmatched_numbers(claim, numbers(source))


def test_a_percent_source_does_not_ground_a_different_percent() -> None:
    # 0.07 과 0.08 의 차이는 정수용 오차 0.5 안에 들어온다. 배율을 따지지
    # 않으면 7% 하나로 0%~57% 주장이 전부 통과했다.
    assert not grounded("7%", "8%")
    assert not grounded("7%", "20%")
    assert not grounded("7%", "57%")
    assert not grounded("42%", "41%")


def test_a_percent_source_still_grounds_the_same_percent() -> None:
    assert grounded("7%", "7%")
    assert grounded("0.07", "7%")
    assert grounded("0.07", "7 percent")
    assert grounded("0.07", "7 퍼센트")


def test_rounding_still_works_at_the_written_precision() -> None:
    # 33.3% 는 소수점 한 자리로 적혔으므로 0.333 ± 0.0005 를 뒷받침한다.
    assert grounded("0.333333", "33.3%")
    assert not grounded("0.333333", "33.9%")


def test_rounding_follows_the_magnitude_word() -> None:
    # '5억'은 0자리로 적혔으니 4.5억 이상 5.5억 미만을 뒷받침한다.
    assert grounded("500000000", "5억")
    assert grounded("460000000", "5억")
    assert not grounded("300000000", "5억")


def test_a_single_percent_source_grounds_almost_nothing_else() -> None:
    source = numbers("7%")
    passing = [
        value for value in range(0, 201)
        if not unmatched_numbers(f"{value}%", source)
    ]

    assert 7 in passing
    assert len(passing) <= 3
