import pytest

from app.agent.query.search_terms import search_terms
from app.agent.tools.workbook_metric_matching import unique_named_metric
from app.agent.tools.workbook_metric_snapshots import build_metric_snapshot


@pytest.mark.parametrize(
    ("header", "question"),
    (
        ("Supplier B Output", "What was Output for supplier A?"),
        ("Plant 2 Output", "Output for Plant 1"),
        ("Region B Revenue", "Revenue for Region A"),
    ),
)
def test_short_row_qualifiers_are_not_dropped(header: str, question: str) -> None:
    comparison = _comparison(header)

    assert unique_named_metric(comparison["metrics"], question) is None
    assert build_metric_snapshot(comparison, question) is None


@pytest.mark.parametrize(
    ("header", "question"),
    (
        ("Cost of Revenue", "매출 최신값"),
        ("Revenue Growth (%)", "매출 최신값"),
        ("Sales & Marketing", "매출 변화"),
        ("Operating Profit Margin", "영업이익 최신값"),
        ("Net Income Margin", "순이익 최신값"),
        ("Free Cash Flow", "현금 최신값"),
        ("Return on Assets", "자산 최신값"),
        ("Debt to Equity", "부채 최신값"),
    ),
)
def test_alias_does_not_select_an_unrequested_derived_metric(
    header: str, question: str
) -> None:
    assert unique_named_metric(_comparison(header)["metrics"], question) is None


@pytest.mark.parametrize(
    ("header", "question", "expected"),
    (
        ("Non-current Assets", "What are current assets?", False),
        ("Non-current Ratio", "current ratio", False),
        ("Current Assets", "What are current assets?", True),
        ("Total Revenue", "매출 최신값", True),
        ("R&D", "What was R&D headcount?", True),
        ("Total Employees", "latest headcount", True),
        ("Sales & Marketing", "Sales & Marketing latest value", True),
        ("Free Cash Flow", "What was Free Cash Flow?", True),
        ("Operating Profit Margin", "Operating Profit Margin latest", True),
    ),
)
def test_alias_modifiers_are_safe_but_common_exact_names_still_work(
    header: str, question: str, expected: bool
) -> None:
    found = unique_named_metric(_comparison(header)["metrics"], question)

    assert (found is not None) is expected


def test_short_identifier_phrase_is_kept_for_row_retrieval() -> None:
    terms = search_terms("What was Output for supplier A?")

    assert "supplier a" in terms
    assert "was" not in terms
    assert "for" not in terms


def test_r_and_d_headcount_uses_r_and_d_as_the_named_metric() -> None:
    comparison = _comparison("R&D")
    comparison.update(
        start_date="2023-12-01", end_date="2023-12-01",
        start_reference="Metrics!A3", end_reference="Metrics!A3",
    )
    comparison["metrics"][0].update(
        start_reference="Metrics!B3", end_reference="Metrics!B3",
    )

    snapshot = build_metric_snapshot(
        comparison, "What was R&D headcount in December 2023?"
    )

    assert snapshot is not None
    assert snapshot["metrics"][0]["header"] == "R&D"


def _comparison(header: str) -> dict:
    return {
        "sheet_name": "Metrics",
        "start_date": "2023-01-01",
        "end_date": "2023-12-01",
        "start_reference": "Metrics!A2",
        "end_reference": "Metrics!A3",
        "metrics": [{
            "header": header,
            "start_value": 10,
            "end_value": 12,
            "change": 2,
            "header_references": ["Metrics!B1"],
            "start_reference": "Metrics!B2",
            "end_reference": "Metrics!B3",
        }],
    }
