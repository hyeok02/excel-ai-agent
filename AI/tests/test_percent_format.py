"""엑셀 서식의 %가 글자인지 배율인지 가려내는지 검증한다."""
from app.services.insights.display.percent_format import scales_by_percent


def test_a_bare_percent_sign_scales_the_number() -> None:
    assert scales_by_percent("0.00%")
    assert scales_by_percent("0%")
    assert scales_by_percent("0.0%;[Red]-0.0%")


def test_a_quoted_percent_sign_is_just_a_letter() -> None:
    """0.00"%" 서식은 18.5를 18.50%로 보여 준다. 100을 곱하면 1,850%가 된다."""
    assert not scales_by_percent('0.00"%"')
    assert not scales_by_percent('#,##0"%"')


def test_an_escaped_percent_sign_is_just_a_letter() -> None:
    assert not scales_by_percent("0.00\\%")


def test_a_format_without_a_percent_sign_scales_nothing() -> None:
    assert not scales_by_percent("#,##0")
    assert not scales_by_percent("")
    assert not scales_by_percent(None)
