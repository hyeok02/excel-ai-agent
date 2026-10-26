"""New cell text must not broaden authorization to duplicate/all source rows."""
import pytest

from tests.support.writeback_target_fixtures import proposal
from tests.test_writeback_semantic_scope import source


def _content(name="Notebook"):
    return source([["Product", "Year", "Status"], [name, 2024, "Open"], [name, 2025, "Open"]])


@pytest.mark.parametrize("particle", ["를", "는"])
@pytest.mark.parametrize("value", ["전체 완료", "모두 완료", "all done", "every item"])
@pytest.mark.parametrize("quoted", [False, True])
def test_quantifier_in_replacement_does_not_choose_an_arbitrary_duplicate(particle, value, quoted):
    replacement = f"'{value}'" if quoted else value
    body = proposal(f"Orders Notebook Status{particle} {replacement}로 수정",
                    [("Orders", "C2", value)], _content())
    assert body["status"] == "blocked" and not body["changes"], body


@pytest.mark.parametrize("name", ["All Services", "전체 서비스"])
def test_quantifier_inside_source_label_does_not_authorize_all_duplicates(name):
    body = proposal(f"Orders {name} Status를 완료로 수정", [("Orders", "C2", "완료")], _content(name))
    assert body["status"] == "blocked", body


@pytest.mark.parametrize("prefix", ["Orders 모든 Notebook Status", "Orders Notebook의 모든 Status"])
def test_explicit_target_quantifier_keeps_all_rows_authorized(prefix):
    body = proposal(f"{prefix}를 '전체 완료'로 수정",
                    [("Orders", "C2", "전체 완료"), ("Orders", "C3", "전체 완료")], _content())
    assert body["status"] == "ready" and len(body["changes"]) == 2, body


def test_new_value_containing_all_still_works_for_a_unique_target():
    content = source([["Product", "Amount", "Status"], ["Notebook", 10, "Open"]])
    body = proposal("Orders Notebook Status를 'all done'으로 수정",
                    [("Orders", "C2", "all done")], content)
    assert body["status"] == "ready", body
