import pytest

from app.agent.query.ambiguity_tables import table_candidates
from app.agent.query.source_record_identity import record_mentioned
from tests.tabular_query_fixtures import table_fixture


def source(names=("Aster Partners Inc.", "Birch Capital Ltd.")):
    blocks = [(top, 1, [["Owner Name", "Amount"], [name, 10], ["Other Holder", 20]])
              for top, name in zip((1, 8), names)]
    return table_fixture(blocks)


@pytest.mark.parametrize("question", ["Aster Partners의 Amount", "Aster Partners Inc.의 Amount"])
def test_legal_suffix_omission_does_not_keep_unrelated_company_tables(question):
    summary, index = source()
    assert table_candidates(question, summary, index) == []


@pytest.mark.parametrize("question", ["Aster의 Amount", "Aster Partners를 제외한 Amount"])
def test_partial_or_excluded_company_names_do_not_select_a_table(question):
    summary, index = source()
    assert len(table_candidates(question, summary, index)) == 2


def test_companies_with_the_same_stem_are_still_ambiguous_even_with_equal_values():
    summary, index = source(("Aster Partners Inc.", "Aster Partners Ltd."))
    assert len(table_candidates("Aster Partners의 Amount", summary, index)) == 2


def test_identical_copies_are_not_collapsed_from_equal_values_without_entity_proof():
    summary, index = source(("Aster Partners Inc.", "Aster Partners Inc."))
    assert len(table_candidates("Aster Partners의 Amount", summary, index)) == 2


def test_requested_identity_is_used_in_the_preview_even_after_the_first_three_rows():
    rows = [[f"Other Holder {index}", index] for index in range(1, 6)]
    blocks = [(top, 1, [["Owner Name", "Amount"], *rows, ["Aster Partners Inc.", value]])
              for top, value in ((1, 77), (12, 88))]
    summary, index = table_fixture(blocks)
    candidates = table_candidates("Aster Partners의 Amount", summary, index)
    assert len(candidates) == 2
    assert "77" in candidates[0].details and "88" in candidates[1].details
    assert all("Aster Partners Inc." in item.details and "Other Holder" not in item.details for item in candidates)


@pytest.mark.parametrize("header,value,question,expected", [
    ("Company", "Alpha Ltd.", "Alpha의 매출", True),
    ("Owner Name", "Alpha Holdings Co. Ltd.", "Alpha Holdings 지분", True),
    ("Company", "Alphabet Inc.", "Alpha 매출", False),
    ("Company", "Alpha Software Inc.", "Alpha 매출", False),
    ("Company", "Alpha Inc.", "except Alpha", False),
    ("Status", "Alpha Inc.", "Alpha", False),
])
def test_only_bounded_source_identity_normalization_is_allowed(header, value, question, expected):
    assert record_mentioned(header, value, question) == expected
