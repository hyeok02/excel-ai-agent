"""Quoted cell text is not sentence punctuation or conjunction grammar."""
import pytest

from tests.test_tabular_explicit_predicates import _run


@pytest.mark.parametrize("literal", [
    "New, Co.", "New and Co", "New or Co", "신규인 항목", "New; Co!", "New rows",
])
@pytest.mark.parametrize("shortened", [False, True])
def test_quoted_contains_value_is_kept_whole(literal, shortened):
    value = literal.split()[0].rstrip(",;") if shortened else literal
    answer = _run(f"Vendor contains '{literal}' rows", [("B", "contains", value)], [
        ["Asset", "Vendor"], ["First", literal + " Ltd"], ["Second", value + " Ventures"],
    ])
    assert (answer is not None) == (not shortened)


@pytest.mark.parametrize("quote", ["'", '"', "‘", "“"])
def test_korean_suffix_is_read_outside_literal(quote):
    close = {"‘": "’", "“": "”"}.get(quote, quote)
    question = f"Vendor가 {quote}New, Co.{close}가 포함된 Asset"
    answer = _run(question, [("B", "contains", "New, Co.")], [
        ["Asset", "Vendor"], ["First", "New, Co. Ltd"], ["Second", "New Ventures"],
    ])
    assert answer is not None
    assert "Asset: First" in answer.answer and "Asset: Second" not in answer.answer


@pytest.mark.parametrize("operator", ["equals", "contains", "not_equals"])
def test_quoted_header_still_preserves_its_explicit_operator(operator):
    answer = _run('"Change" equals New인 Asset', [("D", operator, "New")])
    assert (answer is not None) == (operator == "equals")


def test_header_name_within_a_quoted_value_does_not_start_another_field():
    answer = _run("Vendor contains 'Asset, Co.' rows", [("B", "contains", "Asset, Co.")], [
        ["Asset", "Vendor"], ["First", "Asset, Co. Ltd"], ["Second", "Asset Ventures"],
    ])
    assert answer is not None and "Asset: Second" not in answer.answer


@pytest.mark.parametrize("phrase,expected", [
    ("에 포함된 New인", "contains"), (" includes New인", "contains"),
    (" != New인", "not_equals"), (" ≠ New인", "not_equals"),
    (" not equal to New인", "not_equals"),
])
@pytest.mark.parametrize("column", ["C", "D"])
@pytest.mark.parametrize("operator", ["contains", "not_equals"])
def test_quoted_headers_use_the_same_predicate_grammar(phrase, expected, column, operator):
    answer = _run(f"'Change'{phrase} Asset", [(column, operator, "New")])
    assert (answer is not None) == (column == "D" and operator == expected)
