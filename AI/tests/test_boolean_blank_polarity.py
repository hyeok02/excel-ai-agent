"""Actual blanks are nonmatches for positive labels, not proof of a negative label."""
import pytest

from app.agent.query.boolean_source_answers import boolean_source_answer
from tests.support.large_workbook_fixtures import parsed, tiny_caps, workbook


@pytest.mark.parametrize("streamed", [False, True])
@pytest.mark.parametrize("condition,expected", [
    ("Status = 'x' OR Status = 'o'", 11),
    ("Status contains 'x' OR Status = 'o'", 11),
    ("NOT Status = 'x'", None),
    ("Status != 'x' OR Status = 'o'", None),
    ("NOT (Status = 'x' OR Status = 'o')", None),
    ("NOT NOT (Status = 'x' OR Status = 'o')", 11),
    ("Status is not blank AND NOT Status = 'x'", 5),
])
def test_positive_blank_is_distinguished_from_unknown_negation(request, streamed, condition, expected):
    if streamed:
        request.getfixturevalue("tiny_caps")
    values = ["x"] * 7 + ["o"] * 4 + ["?"] + [None] * 5
    matrix = [["Record", "Status"], *[[f"Item{index}", value] for index, value in enumerate(values)]]
    summary, index, _ = parsed(workbook({"Arbitrary": matrix}))
    answer = boolean_source_answer(condition + " 행 수", summary, index)
    if expected is None:
        assert answer.status == "insufficient_evidence" and answer.verification.level == "unverified"
    else:
        assert answer.status == "answered" and answer.verification.level == "request_checked"
        assert f"{expected}건" in answer.answer
