"""Resolve a missing source-language literal without weakening the scalar guards."""
from dataclasses import replace
from types import SimpleNamespace
import asyncio
import pytest

from app.agent.query.tabular_source_alias_resolution import resolved_source_label_alias_answer
from tests.test_tabular_source_alias import _clarification, _fixture


class Resolver:
    def __init__(self, status="resolved", candidate_id=0):
        self.result = SimpleNamespace(status=status, candidate_id=candidate_id)
        self.calls = []

    async def resolve(self, subject, field, values):
        self.calls.append((subject, field, values))
        return self.result


def _untranslated(question="라일락 직원 수는 몇 명이야?", rows=None):
    args = list(_fixture(question, rows))
    intent = args[3]
    plan = intent.tabular_query
    plan = plan.model_copy(update={"filters": [plan.filters[0].model_copy(update={"value": "라일락"})]})
    args[3] = replace(intent, tabular_query=plan)
    args[-1] = args[-1] or _clarification(question)
    return args


def _answer(*args, resolver):
    return asyncio.run(resolved_source_label_alias_answer(*args, resolver=resolver))


def test_missing_translated_label_is_resolved_against_source_only_and_never_green():
    resolver = Resolver()
    answer = _answer(*_untranslated(), resolver=resolver)
    assert resolver.calls == [("라일락", "Entity", ["Lilac", "Rose"])]
    assert answer is not None and "107" in answer.answer
    assert answer.status == "limited" and answer.verification.level == "source_checked"
    assert "semantic_alias_resolved" in answer.verification.checks
    assert "라일락(Lilac)" in answer.resolved_question


@pytest.mark.parametrize("status,candidate_id", [
    ("ambiguous", 0), ("unmatched", None), ("resolved", None),
    ("resolved", -1), ("resolved", 2), ("resolved", True),
])
def test_invalid_or_ambiguous_candidate_cannot_be_used(status, candidate_id):
    resolver = Resolver(status, candidate_id)
    assert _answer(*_untranslated(), resolver=resolver) is None


@pytest.mark.parametrize("question", [
    "라일락의 2024년 직원 수는 몇 명이야?", "라일락의 정규직 직원 수는 몇 명이야?",
    "라일락과 장미 직원 수는 몇 명이야?", "라일락 Rose 직원 수는 몇 명이야?",
    "라일락의 직원 수와 매출은 얼마야?",
])
def test_unsupported_qualifiers_do_not_even_request_label_resolution(question):
    resolver = Resolver()
    assert _answer(*_untranslated(question), resolver=resolver) is None
    assert not resolver.calls


def test_duplicate_source_rows_are_not_arbitrarily_chosen_after_translation():
    resolver = Resolver()
    args = _untranslated(rows=[["Lilac", 107], ["Lilac", 999]])
    assert _answer(*args, resolver=resolver) is None


def test_existing_korean_source_label_prevents_translation():
    resolver = Resolver()
    args = _untranslated(rows=[["Lilac", 107], ["라일락", 999]])
    assert _answer(*args, resolver=resolver) is None
    assert not resolver.calls


def test_resolver_failure_safely_keeps_the_original_clarification():
    class FailingResolver:
        async def resolve(self, *args):
            raise RuntimeError("unavailable")
    assert _answer(*_untranslated(), resolver=FailingResolver()) is None
