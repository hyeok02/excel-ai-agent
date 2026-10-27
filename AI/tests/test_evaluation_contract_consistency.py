"""All evaluation entry points enforce the same source and badge contracts."""
import asyncio
from copy import deepcopy
import json

import httpx
import pytest

from evals.offline_acceptance import check_case
from evals.run_conversations import check_response
from evals.run_questions import run_case
from tests.support.offline_network import install_network_guard


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    install_network_guard(monkeypatch)


def accepted_response():
    return {"answer": "원본 수량 12", "status": "answered", "confidence": 1,
            "verification": {"level": "request_checked"},
            "evidence": [{"sheet_name": "Right", "reference": "B2"}]}


@pytest.mark.parametrize("change,expected", [
    ({}, None),
    ({"body": {"verification": {"level": "source_checked"}}}, "Request-bound verification missing"),
    ({"case": {"verification_levels": ["source_checked"]}}, "Unexpected verification"),
    ({"case": {"forbid_request_checked": True}}, "Unsupported request-level verification"),
    ({"body": {"evidence": [{"sheet_name": "Wrong", "reference": "B2"}]}}, "Missing source coverage"),
    ({"body": {"evidence": []}}, "Source-bound verification has no valid source references"),
    ({"body": {"answer": "24"}}, "Missing answer pattern"),
    ({"case": {"forbidden_patterns": ["12"]}}, "Forbidden answer pattern"),
    ({"body": {"status": "insufficient_evidence"}}, "status=insufficient_evidence"),
    ({"status": 503}, "HTTP 503"),
])
def test_every_runner_uses_the_same_response_contract(tmp_path, change, expected):
    (tmp_path / "generated.xlsx").write_bytes(b"offline transport fixture")
    case = {"id": "same", "file": "generated.xlsx", "question": "수량은?", "required_patterns": ["12"],
            "evidence_targets": ["Right!B2"], "verified": True, **change.get("case", {})}
    body = {**deepcopy(accepted_response()), **change.get("body", {})}
    status = change.get("status", 200)
    direct = check_response(case, status, body)
    assert check_case(case, status, body) == direct

    async def evaluate():
        transport = httpx.MockTransport(lambda request: httpx.Response(status, json=body))
        async with httpx.AsyncClient(transport=transport) as client:
            return await run_case(client, asyncio.Semaphore(1), case, tmp_path, "http://offline/questions")

    result = asyncio.run(evaluate())
    assert result["errors"] == direct
    assert result["strict_answer_errors"] == direct
    if expected is None:
        assert direct == []
    else:
        assert any(expected in error for error in direct), direct


def test_default_status_is_not_an_abstention_success_for_any_runner():
    body = {"status": "insufficient_evidence", "answer": "수량 12는 확인 불가"}
    assert check_response({"required_patterns": ["12"]}, 200, body)
    assert check_case({"required_patterns": ["12"]}, 200, body)


@pytest.mark.parametrize("level", ["source_checked", "request_checked"])
@pytest.mark.parametrize("evidence", [None, [], [{"sheet_name": "Right", "reference": "not a cell"}]])
def test_badge_without_real_source_references_never_passes(level, evidence):
    body = {"status": "answered", "answer": "12", "verification": {"level": level}, "evidence": evidence}
    assert any("no valid source references" in error for error in check_response({}, 200, body))


@pytest.mark.parametrize("body", [None, [], "12", {"answer": 12, "status": "answered"},
                                      {"answer": "12", "status": "answered", "verification": "checked"}])
def test_malformed_response_is_an_explicit_evaluation_failure(body):
    assert check_response({}, 200, body)
    assert check_case({}, 200, body)


@pytest.mark.parametrize("body", [None, [], "12"])
def test_question_runner_retains_invalid_json_shape_and_shared_errors(tmp_path, body):
    (tmp_path / "generated.xlsx").write_bytes(b"offline transport fixture")
    case = {"id": "invalid", "file": "generated.xlsx", "question": "수량은?"}

    async def evaluate():
        transport = httpx.MockTransport(lambda request: httpx.Response(
            200, content=json.dumps(body), headers={"content-type": "application/json"}))
        async with httpx.AsyncClient(transport=transport) as client:
            return await run_case(client, asyncio.Semaphore(1), case, tmp_path, "http://offline/questions")

    result = asyncio.run(evaluate())
    assert result["response"] == body
    assert result["errors"] == check_response(case, 200, body)
