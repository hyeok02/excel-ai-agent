from dataclasses import replace

import pytest
from pydantic import ValidationError

from app.agent.query.clarification_models import SourceClarificationOption
from app.agent.query.conversation_models import QuestionConversation
from app.agent.query.models import QuestionAnswer
from tests.support.clarification_fixtures import fixture, initial


@pytest.mark.parametrize("field,value", [
    ("source_question", "x"), ("source_question", "x" * 1001),
    ("option_id", "a" * 63), ("option_id", "a" * 65), ("option_id", "A" * 64),
    ("value", 999), ("evidence", ["Sheet!A1"]), ("question", "injected"),
])
def test_selection_rejects_invalid_bounds_or_client_facts(field, value):
    payload = {"source_question": "Revenue 합계는?", "option_id": "a" * 64, field: value}
    with pytest.raises(ValidationError):
        QuestionConversation(selection=payload)


@pytest.mark.parametrize("field,value", [
    ("label", "x" * 201), ("scope", "x" * 201), ("details", "x" * 1001),
    ("question", "x" * 1001), ("id", "a" * 65), ("value", 999),
])
def test_option_contract_is_bounded_and_has_no_factual_value_field(field, value):
    payload = {"id": "a" * 64, "label": "Label", "scope": "Scope", "details": "",
               "question": "Question", field: value}
    with pytest.raises(ValidationError):
        SourceClarificationOption(**payload)


def test_legacy_answer_defaults_to_no_choices_and_choice_count_is_bounded():
    summary, index = fixture()
    answer = initial(summary, index)
    payload = answer.model_dump()
    payload.pop("clarification_options")
    assert QuestionAnswer(**payload).clarification_options == []
    payload["clarification_options"] = answer.clarification_options * 4
    with pytest.raises(ValidationError):
        QuestionAnswer(**payload)


def test_overlong_canonical_question_cannot_be_sent_as_option():
    summary, index = fixture()
    question = "Revenue 합계는? " + "아" * 975
    answer = initial(summary, index, question)
    assert answer.status == "insufficient_evidence"
    assert answer.clarification_options == []


def test_content_digest_changes_identifier_even_when_source_labels_are_identical():
    summary, index = fixture()
    first = initial(summary, index)
    second = initial(summary, replace(index, source_digest="b" * 64))
    assert {choice.question for choice in first.clarification_options} == {
        choice.question for choice in second.clarification_options}
    assert not ({choice.id for choice in first.clarification_options}
                & {choice.id for choice in second.clarification_options})
