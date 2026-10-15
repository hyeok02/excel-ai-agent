import pytest

from app.agent.query.search_terms import search_terms
from app.agent.tools.workbook_metric_changes import build_metric_change
from app.agent.tools.workbook_metric_matching import unique_named_metric
from app.agent.tools.workbook_metric_snapshots import build_metric_snapshot


@pytest.mark.parametrize(
    ("header", "question"),
    (
        ("Revenue", "매출원가 변화"),
        ("영업", "영업이익 변화"),
        ("Total Revenue", "IT revenue change"),
        ("Output", "What was Output for supplier A?"),
    ),
)
def test_additional_metric_or_row_conditions_are_not_ignored(
    header: str, question: str
) -> None:
    comparison = _comparison([header])

    assert unique_named_metric(comparison["metrics"], question) is None
    assert build_metric_snapshot(comparison, question) is None
    assert build_metric_change(comparison, question) is None


@pytest.mark.parametrize(
    ("header", "question"),
    (
        ("Total Revenue", "매출 변화"),
        ("Operating Profit", "영업이익 변화"),
        ("Research & Development", "R&D의 직원 수 변화"),
    ),
)
def test_exact_semantic_metric_aliases_still_match(
    header: str, question: str
) -> None:
    found = unique_named_metric(_comparison([header])["metrics"], question)

    assert found is not None and found["header"] == header


@pytest.mark.parametrize(
    ("header", "question"),
    (
        ("Total Employees", "직원수 최신값"),
        ("Total Revenue", "매출액 최신값"),
        ("Total Revenue", "총매출 최신값"),
        ("Research & Development", "연구개발인원 최신값"),
        ("재료비", "재료비 최신값"),
        ("생산인원", "생산인원 최신값"),
        ("Output", "latest Output"),
    ),
)
def test_common_compounds_and_latest_value_words_match(
    header: str, question: str
) -> None:
    found = unique_named_metric(_comparison([header])["metrics"], question)

    assert found is not None and found["header"] == header


def test_numbered_korean_headers_do_not_tie_on_the_generic_noun() -> None:
    metrics = _comparison(["1공장", "2공장"])["metrics"]

    found = unique_named_metric(metrics, "1공장 최신 사용량")

    assert found is not None and found["header"] == "1공장"


def test_latest_value_word_does_not_hide_numbered_korean_header() -> None:
    found = unique_named_metric(_comparison(["1공장"])["metrics"], "1공장 최신값")

    assert found is not None and found["header"] == "1공장"


@pytest.mark.parametrize(
    ("header", "question"),
    (
        ("재료비", "2025년 3월 재료비는?"),
        ("재료비", "2025년3월 재료비는?"),
        ("재료비", "2025년3월15일 재료비는?"),
        ("재료비", "2025-03-15 재료비는?"),
        ("Output", "Output in March 2025"),
    ),
)
def test_date_words_do_not_hide_an_exact_metric(header: str, question: str) -> None:
    found = unique_named_metric(_comparison([header])["metrics"], question)

    assert found is not None and found["header"] == header


def test_search_terms_preserve_real_words_ending_in_subject_particles() -> None:
    assert "원가" in search_terms("원가")
    assert "원" not in search_terms("원가")
    assert "차이" in search_terms("차이")
    assert "차" not in search_terms("차이")
    assert "원가" in search_terms("원가가 변했어?")


def test_r_and_d_with_a_korean_particle_is_normalized() -> None:
    terms = set(search_terms("R&D의 직원 수"))

    assert {"연구개발", "research", "development"} <= terms


def _comparison(headers: list[str]) -> dict:
    return {
        "sheet_name": "Metrics",
        "start_date": "2025-01-01",
        "end_date": "2025-06-01",
        "start_reference": "Metrics!A2",
        "end_reference": "Metrics!A3",
        "metrics": [_metric(header, index) for index, header in enumerate(headers, 2)],
    }


def _metric(header: str, column: int) -> dict:
    letter = chr(64 + column)
    return {
        "header": header,
        "start_value": 10,
        "end_value": 12,
        "change": 2,
        "header_references": [f"Metrics!{letter}1"],
        "start_reference": f"Metrics!{letter}2",
        "end_reference": f"Metrics!{letter}3",
    }
