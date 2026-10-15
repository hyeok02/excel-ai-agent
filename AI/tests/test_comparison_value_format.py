import pytest

from app.agent.query.comparison_value_format import (
    comparison_values,
    people_unit,
)
from app.agent.query.metric_change_answers import _text
from app.agent.tools.workbook_metric_changes import build_metric_change


def test_fractional_percent_values_use_percent_and_percentage_points() -> None:
    assert comparison_values(0.1, 0.2, 0.1, "0%", "0%") == (
        "10%",
        "20%",
        "10%p",
    )


def test_currency_symbol_and_precision_are_preserved() -> None:
    assert comparison_values(1200, 1530.5, 330.5, "$#,##0.00", "$#,##0.00") == (
        "$1,200.00",
        "$1,530.50",
        "$330.50",
    )


def test_locale_marker_without_currency_does_not_invent_dollar_unit() -> None:
    assert comparison_values(10, 12, 2, "[$-409]0", "[$-409]0") == (
        "10", "12", "2",
    )


def test_quoted_literal_unit_is_preserved_instead_of_fallback_unit() -> None:
    assert comparison_values(12, 15, 3, '#,##0 "개"', '#,##0 "개"', "명") == (
        "12개",
        "15개",
        "3개",
    )


def test_trailing_commas_apply_excel_thousand_scaling() -> None:
    assert comparison_values(
        1_200_000, 1_500_000, 300_000,
        '#,##0,"천원"', '#,##0,"천원"',
    ) == ("1,200천원", "1,500천원", "300천원")
    assert comparison_values(
        1_200_000, 1_500_000, 300_000,
        '#,##0.0,,"M"', '#,##0.0,,"M"',
    ) == ("1.2M", "1.5M", "0.3M")


def test_elapsed_hour_format_uses_excel_day_fraction_semantics() -> None:
    assert comparison_values(1.5, 2.25, 0.75, "[h]:mm", "[h]:mm") == (
        "36:00", "54:00", "18:00",
    )


def test_general_format_preserves_small_and_precise_values() -> None:
    assert comparison_values(0.001, 0.002, 0.001) == (
        "0.001", "0.002", "0.001",
    )
    precise = 0.1234567890123456
    assert comparison_values(precise, precise, 0)[0] == repr(precise)


def test_unsupported_fraction_and_clock_formats_use_raw_values() -> None:
    assert comparison_values(1.5, 1.75, 0.25, "# ?/?", "# ?/?") == (
        "1.5", "1.75", "0.25",
    )
    assert comparison_values(0.5, 0.75, 0.25, "h:mm", "h:mm") == (
        "0.5", "0.75", "0.25",
    )


def test_unsafe_quoted_literal_is_not_copied_to_answer() -> None:
    values = comparison_values(10, 12, 2, '0 "=cmd"', '0 "=cmd"')

    assert values == ("10", "12", "2")


def test_explain_request_does_not_invent_people_unit() -> None:
    assert people_unit("매출 변화를 설명해줘", "매출") == ""
    assert people_unit("설명은 짧게 해줘", "매출") == ""
    assert people_unit("직원 수 변화를 설명해줘", "직원 수") == "명"
    assert people_unit("몇 명 줄었어?", "서비스") == "명"


@pytest.mark.parametrize(
    "header",
    ("Revenue per Employee", "Employee Cost", "직원 만족도", "인원당 매출"),
)
def test_employee_related_non_count_metrics_do_not_get_people_unit(header: str) -> None:
    assert people_unit(f"{header} 변화", header) == ""


@pytest.mark.parametrize(
    "header", ("Total Employees", "Employee Count", "Headcount", "직원수", "인원")
)
def test_explicit_headcount_metrics_keep_people_unit(header: str) -> None:
    assert people_unit(f"{header} 변화", header) == "명"


def test_metric_change_uses_percentage_point_display_without_relative_share() -> None:
    answer = _text(
        "전환율 변화를 설명해줘",
        {
            "header": "전환율",
            "start_value": 0.1,
            "end_value": 0.2,
            "change": 0.1,
            "start_number_format": "0%",
            "end_number_format": "0%",
        },
    )

    assert answer == "전환율은 10%에서 20%으로 10%p 증가했습니다."
    assert "100.0%" not in answer


def test_metric_change_explain_request_has_no_people_unit() -> None:
    answer = _text(
        "매출 변화를 설명해줘",
        {"header": "매출", "start_value": 100, "end_value": 120, "change": 20},
    )

    assert "100에서 120으로 20(20.0%) 증가" in answer
    assert "명" not in answer


def test_named_metric_payload_keeps_endpoint_number_formats() -> None:
    comparison = {"metrics": [{
        "header": "Rate", "start_value": 0.1, "end_value": 0.2,
        "change": 0.1, "start_number_format": "0%", "end_number_format": "0.0%",
        "header_references": ["Metrics!B1"],
        "start_reference": "Metrics!B2", "end_reference": "Metrics!B3",
    }]}

    found = build_metric_change(comparison, "Rate 변화")

    assert found is not None
    assert found["start_number_format"] == "0%"
    assert found["end_number_format"] == "0.0%"
