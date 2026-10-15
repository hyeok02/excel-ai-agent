import asyncio

import httpx
import pytest

from evals.run_questions import evidence_errors, run_case


def test_evaluation_requires_the_correct_source_sheet_and_entire_range():
    sources = [{"sheet_name": "Source", "reference": "B1:B3"},
               {"sheet_name": "Source", "reference": "C2"}]
    assert evidence_errors(["Source!B2:C2"], sources) == []
    assert evidence_errors(["Source!B2:C3"], sources)
    assert evidence_errors(["Other!B2"], sources)
    assert evidence_errors(["Source!B2"], [{"reference": "invalid"}])


@pytest.mark.parametrize("allowed,level,accepted", [
    (True, "unverified", True), (False, "unverified", False),
    (True, "request_checked", False),
])
def test_clarification_does_not_erase_strict_answer_failures(tmp_path, allowed, level, accepted):
    (tmp_path / "source.xlsx").write_bytes(b"fixture")
    case = {"id": "ambiguous", "file": "source.xlsx", "question": "Amount 합계", "required_patterns": ["100"]}
    body = {"answer": "다시 질문: Source 시트의 Amount 합계", "status": "insufficient_evidence",
            "confidence": 0, "verification": {"level": level}, "selected_tools": ["clarify_source_scope"],
            "evidence": [{"sheet_name": "Source", "reference": "B1"},
                         {"sheet_name": "Other", "reference": "B1"}]}

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body))) as client:
            return await run_case(client, asyncio.Semaphore(1), case, tmp_path, "http://test/questions",
                                  ["ambiguous"] if allowed else [])
    result = asyncio.run(check())
    assert bool(result["errors"]) is not accepted
    assert result["strict_answer_errors"]  # Never count clarification as a numeric answer pass.
    assert (result["outcome"] == "scope_clarification") is accepted
