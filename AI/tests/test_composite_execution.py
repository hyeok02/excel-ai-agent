"""Original request coverage, isolated failures and per-part evidence offline."""
import asyncio
from types import SimpleNamespace

import pytest

from app.agent.query.composite_execution import composite_answer
from app.agent.query.composite_models import CompositeQueryPlan, CompositeQuestionPart
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.models import QuestionAnswer, QuestionAnswerEvidence, QuestionAnswerVerification
from tests.support.large_workbook_fixtures import offline


def answer(question, *, status="answered", level="request_checked", value="10"):
    return QuestionAnswer(question=question, answer=value, status=status, confidence=.99,
                          selected_tools=["tabular_query"], evidence=[QuestionAnswerEvidence(
                              kind="cell", sheet_name="Records", reference="B2", label="Amount", description="source", value=10)],
                          limitations=[], verification=QuestionAnswerVerification(level=level, checks=["calculation", "request_alignment"]))


def intent(parts, prefix=""):
    return QuestionIntent(False, composite_query=CompositeQueryPlan(
        shared_prefix=prefix, parts=[CompositeQuestionPart(source_text=text) for text in parts]))


def run(question, proposal, callback):
    return asyncio.run(composite_answer(question, SimpleNamespace(resolutions={}), proposal, callback))


def test_complete_subanswers_preserve_source_labels_and_request_coverage():
    calls = []

    async def callback(question, sources, **options):
        calls.append((question, options))
        return answer(question)

    found = run("Amount 합계; Customer 수", intent(["Amount 합계", "Customer 수"]), callback)
    assert found.status == "answered" and found.verification.level == "request_checked"
    assert "compound_request_coverage" in found.verification.checks
    assert "compound_parts_2" in found.verification.checks
    assert "문항 1" in found.evidence[0].label and "문항 2" in found.evidence[1].label
    assert all(not options["allow_composite"] and not options["allow_replan"] for _, options in calls)


@pytest.mark.parametrize("parts,prefix", [(["Amount 합계", "다른 질문"], ""),
                                         (["Customer 수", "Amount 합계"], ""),
                                         (["Amount 합계", "Customer 수"], "Status=active")])
def test_model_cannot_rewrite_reorder_or_invent_scope(parts, prefix):
    async def callback(*args, **kwargs):
        raise AssertionError("Changed source coverage must never execute")

    found = run("Amount 합계; Customer 수", intent(parts, prefix), callback)
    assert found.status == "insufficient_evidence" and found.verification.level == "unverified"


def test_unsupported_dependent_part_keeps_good_answer_without_whole_green_badge():
    calls = []

    async def callback(question, sources, **options):
        calls.append(question)
        return answer(question)

    found = run("Amount 합계; 그중 상위 3개", intent(["Amount 합계", "그중 상위 3개"]), callback)
    assert calls == ["Amount 합계"]
    assert found.status == "limited" and found.verification.level == "source_checked"
    assert "10" in found.answer and "확인 불가" in found.answer and len(found.evidence) == 1
    assert "compound_request_coverage" not in found.verification.checks


@pytest.mark.parametrize("failure", ["exception", "unverified", "limited", "rewritten"])
def test_one_failed_part_never_borrows_another_parts_verification(failure):
    async def callback(question, sources, **options):
        if question == "Amount 합계":
            return answer(question)
        if failure == "exception":
            raise ValueError("private internal details")
        if failure == "unverified":
            return answer(question, level="unverified", value="WRONG_UNCHECKED_999")
        if failure == "limited":
            return answer(question, status="limited", level="source_checked")
        return answer("Some other question")

    found = run("Amount 합계; Customer 수", intent(["Amount 합계", "Customer 수"]), callback)
    assert found.status == "limited" and found.verification.level != "request_checked"
    assert "private internal details" not in found.answer and "WRONG_UNCHECKED_999" not in found.answer


def test_deterministic_offline_decomposition_needs_no_composite_model():
    calls = []

    async def callback(question, sources, **options):
        calls.append(question)
        assert options["intent_override"] is None
        return answer(question)

    found = run("Records 시트: Amount 합계; Customer 수", None, callback)
    assert calls == ["Records 시트 Amount 합계", "Records 시트 Customer 수"]
    assert found.verification.level == "request_checked"


@pytest.mark.parametrize("missing", ["evidence", "request_alignment", "limitations"])
def test_a_success_label_without_actual_proof_never_makes_whole_answer_green(missing):
    async def callback(question, sources, **options):
        result = answer(question)
        if question == "Customer 수":
            if missing == "evidence":
                result.evidence = []
            elif missing == "request_alignment":
                result.verification.checks = ["calculation"]
            else:
                result.limitations = ["Only part of the requested source was checked"]
        return result

    found = run("Amount 합계; Customer 수", intent(["Amount 합계", "Customer 수"]), callback)
    assert found.status == "limited" and found.verification.level != "request_checked"


def test_part_interpretation_is_finished_before_composition():
    async def callback(question, sources, **options):
        return answer(question)

    found = run("Amount 합계; Customer 수가 왜 늘었어?", intent(["Amount 합계", "Customer 수가 왜 늘었어?"]), callback)
    assert found.status == "limited" and found.verification.level == "source_checked"
    assert any("의미·원인" in note and "문항 2" in note for note in found.limitations)
