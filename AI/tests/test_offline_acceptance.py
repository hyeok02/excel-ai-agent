"""No model/network fallback and no success by abstaining from normal requests."""
import asyncio
import socket

import pytest

from evals.offline_acceptance import check_case, validate_cases
from evals.offline_api import ModelRequired, NoModel, offline_client
from tests.support.offline_network import ExternalNetworkForbidden


def test_normal_answer_cannot_pass_by_abstaining():
    assert check_case({"required_patterns": ["12"]}, 200,
                      {"status": "insufficient_evidence", "answer": "확인 불가"})


def test_correct_number_from_wrong_source_does_not_pass():
    assert check_case({"required_patterns": ["12"], "evidence_targets": ["Right!B2"]},
                      200, {"status": "answered", "answer": "12",
                            "evidence": [{"sheet_name": "Wrong", "reference": "B2"}]})


def test_negative_case_rejects_false_verification():
    assert check_case({"statuses": ["insufficient_evidence"], "verification_levels": ["unverified"]},
                      200, {"status": "insufficient_evidence", "verification": {"level": "source_checked"}})


_CASE = {"id": "a", "file": "one", "question": "수량은?", "required_patterns": ["12"]}


@pytest.mark.parametrize("cases, reason", [
    ([], "No acceptance"),
    ([{**_CASE, "parent": "missing"}], "Parent must precede"),
    ([_CASE, dict(_CASE)], "Duplicate case"),
    ([_CASE, {**_CASE, "id": "b", "file": "two", "parent": "a"}], "same file"),
])
def test_missing_coverage_and_invalid_history_fail(cases, reason):
    with pytest.raises(ValueError, match=reason):
        validate_cases(cases)


def test_status_alone_is_not_an_acceptance_oracle():
    with pytest.raises(ValueError, match="independent"):
        validate_cases([{"id": "anything", "file": "source.xlsx", "question": "수량은?"}])


def test_strict_questions_and_same_file_history_are_accepted():
    base = {"file": "source.xlsx", "question": "수량은?", "required_patterns": ["12"]}
    validate_cases([{**base, "id": "a"}, {**base, "id": "b", "parent": "a"}])


def test_offline_client_blocks_network_and_model_and_restores_overrides():
    from app.main import app
    original = app.dependency_overrides.copy()

    async def check():
        async with offline_client() as client:
            assert (await client.get("/health")).status_code == 200
            with pytest.raises(ExternalNetworkForbidden):
                socket.create_connection(("example.invalid", 443))
            with pytest.raises(ModelRequired):
                await NoModel().generate()
    asyncio.run(check())
    assert app.dependency_overrides == original
