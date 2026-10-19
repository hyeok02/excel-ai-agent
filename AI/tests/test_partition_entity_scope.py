"""A source row rank cannot certify a person count without whole-group identity proof."""
import pytest

from tests.support.advanced_qna_fixtures import checked, partition_plan, source
from tests.support.large_workbook_fixtures import ask, assert_not_certified, offline, tiny_caps

QUESTION = "Records 시트 각 Department별 Amount 상위 2명 Name과 Amount 보여줘"


def people(*, duplicate=False):
    return [["Name", "Amount", "Department"],
            ["Alex", 100, "Alpha"], ["Bo", 30, "Alpha"],
            ["Alex", 70, "Beta"], ["Alex" if duplicate else "Casey", 1, "Alpha"]]


@pytest.mark.parametrize("streamed", [True, False])
def test_people_rank_checks_unique_identities_in_each_entire_group(streamed, request):
    if streamed:
        request.getfixturevalue("tiny_caps")
    summary, index, _ = source(people())
    answer = ask(QUESTION, summary, index, partition_plan(summary, identity_column_ids=["A"]))
    checked(answer, scan=streamed)
    assert "Name: Alex" in answer.answer and "Name: Bo" in answer.answer
    assert "Name: Casey" not in answer.answer


def test_late_repeated_person_cannot_hide_below_retained_winners(tiny_caps):
    summary, index, _ = source(people(duplicate=True))
    answer = ask(QUESTION, summary, index, partition_plan(summary, identity_column_ids=["A"]))
    assert_not_certified(answer)


@pytest.mark.parametrize("identities", [[], ["B"], ["C"]])
def test_omitted_or_measure_group_identity_is_not_evidence_of_distinct_people(identities, tiny_caps):
    summary, index, _ = source(people(duplicate=True))
    answer = ask(QUESTION, summary, index, partition_plan(summary, identity_column_ids=identities))
    assert_not_certified(answer)
