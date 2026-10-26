"""Deletion words in new text and negated instructions never authorize null."""
import pytest

from app.agent.writeback.value_authorization import value_is_authorized
from tests.support.writeback_target_fixtures import proposal
from tests.test_writeback_semantic_scope import source


@pytest.mark.parametrize("operation", ["'삭제하지 마세요'로 수정", "'delete me'로 수정",
                                      "삭제하지 마", "지우지 마세요", "do not delete", "don't clear",
                                      "삭제 완료로 수정", "clearance로 수정"])
def test_literal_or_negated_deletion_never_authorizes_null(operation):
    assert not value_is_authorized(None, operation)
    content = source([["Product", "Amount", "Status"], ["Notebook", 10, "Open"]])
    body = proposal(f"Orders Notebook Status를 {operation}", [("Orders", "C2", None)], content)
    assert body["status"] == "blocked" and not body["changes"], body


@pytest.mark.parametrize("operation", ["삭제해줘", "삭제", "지워줘", "비워줘", "비우고", "clear", "delete", "remove"])
def test_affirmative_clear_operations_remain_usable(operation):
    assert value_is_authorized(None, operation)
    content = source([["Product", "Amount", "Status"], ["Notebook", 10, "Open"]])
    body = proposal(f"Orders Notebook Status를 {operation}", [("Orders", "C2", None)], content)
    assert body["status"] == "ready" and body["changes"][0]["new_value"] is None, body


@pytest.mark.parametrize("value", ["삭제하지 마세요", "delete me", "clearance"])
def test_literal_text_with_deletion_words_can_be_written_as_text(value):
    content = source([["Product", "Amount", "Status"], ["Notebook", 10, "Open"]])
    body = proposal(f"Orders Notebook Status를 '{value}'로 수정", [("Orders", "C2", value)], content)
    assert body["status"] == "ready" and body["changes"][0]["new_value"] == value, body


@pytest.mark.parametrize("instruction", ["replace Orders C2 with delete", "fill Orders C2 with clear",
                                        "write remove into Orders C2", "set Orders C2 to delete"])
def test_english_text_assignment_cannot_be_replaced_by_a_clear(instruction):
    assert not value_is_authorized(None, instruction)
    content = source([["Product", "Amount", "Status"], ["Notebook", 10, "Open"]])
    body = proposal(instruction, [("Orders", "C2", None)], content)
    assert body["status"] == "blocked" and not body["changes"], body


def test_english_replace_keeps_the_requested_literal_text():
    content = source([["Product", "Amount", "Status"], ["Notebook", 10, "Open"]])
    body = proposal("replace Orders C2 with delete", [("Orders", "C2", "delete")], content)
    assert body["status"] == "ready" and body["changes"][0]["new_value"] == "delete", body
