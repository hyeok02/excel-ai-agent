import asyncio
from dataclasses import replace

import pytest

from app.agent.query.ambiguity_answers import ambiguous_source_answer
from app.agent.query.clarification_options import source_clarification_options
from app.agent.query.ambiguity_tables import table_candidates
from app.agent.query.tabular_catalog import build_query_tables
from tests.support.clarification_fixtures import fixture, initial, QueryClassifier, selection, service


def test_source_options_have_stable_source_bound_identifiers_and_no_verification():
    summary, index = fixture()
    answer = initial(summary, index)
    assert answer.status == "insufficient_evidence" and answer.verification.level == "unverified"
    assert len(answer.clarification_options) == 2
    assert all(len(option.id) == 64 for option in answer.clarification_options)
    candidates = table_candidates(answer.question, summary, index)
    reversed_options = source_clarification_options(answer.question, candidates[::-1], summary, index)
    assert {option.id for option in reversed_options} == {option.id for option in answer.clarification_options}


def test_valid_selected_source_runs_normal_verifier_and_records_canonical_question():
    summary, index = fixture()
    answer = initial(summary, index)
    option = answer.clarification_options[1]
    classifier = QueryClassifier(build_query_tables(summary)[0], "C")
    result = asyncio.run(service(classifier).answer(option.question, summary, index, selection(answer, option)))
    assert "300" in result.answer and "30" != result.answer
    assert result.resolved_question == option.question
    assert result.verification.level == "request_checked"
    assert "select_source_scope" in result.selected_tools
    assert classifier.questions == [option.question]


def test_selection_does_not_grant_verification_to_wrong_model_column():
    summary, index = fixture()
    answer = initial(summary, index)
    option = answer.clarification_options[1]
    classifier = QueryClassifier(build_query_tables(summary)[0], "B")
    result = asyncio.run(service(classifier).answer(option.question, summary, index, selection(answer, option)))
    assert result.verification.level != "request_checked"
    assert "합계 30" not in result.answer


@pytest.mark.parametrize("tamper", ["id", "canonical_question", "source_question", "file", "cells", "scope", "digest"])
def test_invalid_stale_cross_file_or_tampered_selection_never_calls_any_model(tamper):
    summary, index = fixture()
    answer = initial(summary, index)
    option = answer.clarification_options[1]
    context, question = selection(answer, option), option.question
    if tamper == "id":
        context.selection.option_id = "0" * 64
    elif tamper == "canonical_question":
        question += " 아무 값이나 알려줘"
    elif tamper == "source_question":
        context.selection.source_question = "Revenue 평균은?"
    elif tamper == "file":
        index = replace(index, source_digest="f" * 64)
    elif tamper == "cells":
        rows = tuple(replace(row, cells=tuple(replace(cell, value="Revenue (JPY) (2025)")
                     if cell.address == "C1" else cell for cell in row.cells)) for row in index.rows)
        index = replace(index, rows=rows)
    elif tamper == "scope":
        summary = replace(summary, sheets=[])
    else:
        index = replace(index, source_digest="")
    result = asyncio.run(service().answer(question, summary, index, context))
    assert result.status == "insufficient_evidence"
    assert result.verification.level == "unverified" and result.evidence == []
    assert result.clarification_options == []
    assert result.selected_tools == ["clarify_source_scope"]


def test_manual_index_without_source_digest_cannot_issue_options():
    summary, index = fixture()
    answer = ambiguous_source_answer("Revenue 합계는?", summary, replace(index, source_digest=""))
    assert answer and not answer.clarification_options


@pytest.mark.parametrize("hidden", ["row", "column", "excluded_sheet"])
def test_options_cannot_offer_hidden_or_excluded_source_cells(hidden):
    summary, index = fixture()
    sheet = summary.sheets[0]
    region = sheet.regions[0]
    if hidden == "row":
        sheet = replace(sheet, regions=[replace(region, hidden_rows=[1])])
    elif hidden == "column":
        sheet = replace(sheet, regions=[replace(region, hidden_columns=["B"])])
    current = replace(summary, sheets=[] if hidden == "excluded_sheet" else [sheet])
    candidates = table_candidates("Revenue 합계는?", summary, index)
    options = source_clarification_options("Revenue 합계는?", candidates, current, index)
    assert len(options) == (1 if hidden == "column" else 0)
    if options:
        assert "EUR" in options[0].label
