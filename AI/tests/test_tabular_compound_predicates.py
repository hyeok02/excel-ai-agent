"""An understood first predicate cannot hide an unsupported second one."""
import pytest

from tests.test_tabular_explicit_predicates import _run


_MATRIX = [
    ["Asset", "Vendor"], ["First", "New, Co. Ltd."],
    ["Second", "New Ventures"], ["Third", "Old, Co."],
]


@pytest.mark.parametrize("question", [
    "Vendor contains 'New' and 'Co.' rows",
    "Vendor contains 'New' but not 'Ventures' rows",
    "Vendor contains 'New' except 'Ventures' rows",
    "Vendor contains New and Co. rows",
    "Vendor contains New, Co. rows",
    "Vendor가 'New'가 포함되며 'Co.'가 포함된 Asset",
    "Vendor가 'New'이고 'Co.'인 Asset",
    "Vendor contains New이고 Co.인 Asset",
    "Vendor contains 'New'이며 Co.가 포함된 Asset",
    "Vendor contains 'New' rows without Ventures",
    "Vendor contains 'New' Asset but not 'Ventures'",
])
@pytest.mark.parametrize("extra", [False, True])
def test_unparsed_same_field_condition_cannot_disappear_or_be_guessed(question, extra):
    filters = [("B", "contains", "New")]
    if extra:
        filters.append(("B", "not_equals", "Ventures"))
    assert _run(question, filters, _MATRIX) is None


@pytest.mark.parametrize("question", [
    "Vendor contains 'New, Co.' rows", 'Vendor contains "New, Co." rows',
    "Vendor가 'New, Co.'가 포함된 Asset", "Vendor contains New rows",
    "Vendor contains New.", "Vendor contains New, rows",
])
def test_single_literal_and_sentence_punctuation_remain_supported(question):
    value = "New, Co." if "New, Co." in question else "New"
    answer = _run(question, [("B", "contains", value)], _MATRIX)
    assert answer is not None and answer.verification.level == "request_checked"


@pytest.mark.parametrize("separator", [",", "and", "이고"])
def test_next_explicit_field_binds_its_own_predicate(separator):
    question = f"Vendor contains 'New' {separator} Review가 approved인 Asset"
    answer = _run(question, [("B", "contains", "New"), ("C", "equals", "approved")], [
        ["Asset", "Vendor", "Review"], ["First", "New Co", "approved"],
        ["Second", "New Ventures", "pending"],
    ])
    assert answer is not None
    assert "Asset: First" in answer.answer and "Asset: Second" not in answer.answer


@pytest.mark.parametrize("literal", ["New and Co", "New or Co", "신규인 항목", "New, Co."])
def test_conjunctions_inside_one_literal_are_not_a_second_predicate(literal):
    answer = _run(f"Vendor contains '{literal}' rows", [("B", "contains", literal)], [
        ["Asset", "Vendor"], ["First", literal + " Ltd"], ["Second", "Unrelated"],
    ])
    assert answer is not None and "Asset: Second" not in answer.answer


def test_annotated_category_fallback_cannot_ignore_a_tail_after_an_output_header():
    from app.agent.query.tabular_partial_categories import partial_category_answer
    from tests.test_tabular_partial_category_answer import _fixture

    question = "State가 x인 Asset 중 Change가 New인 Asset but not 'scheduled'"
    assert partial_category_answer(*_fixture(question)) is None
