"""Run a user-supplied workbook/Q&A manifest against the real HTTP pipeline.

Workbook paths and expected answers belong to the evaluation manifest, never to
application routing. No workbook is modified and no macros are executed here.
The JSON report retains every response so a passing pattern check is not mistaken
for an independent semantic audit.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import httpx

if __package__:
    from .response_checks import check_response, evidence_errors
else:
    from response_checks import check_response, evidence_errors


async def run_case(client, semaphore, case, directory, endpoint, allow_clarification=()):
    path = directory / case["file"]
    async with semaphore:
        started = time.monotonic()
        try:
            response = await client.post(endpoint, data={"question": case["question"]},
                                         files={"file": (path.name, path.read_bytes())})
            body = response.json()
            errors = check_response(case, response.status_code, body)
            strict_errors = list(errors)
            fields = body if isinstance(body, dict) else {}
            clarified = (case["id"] in allow_clarification and response.status_code == 200
                         and fields.get("status") == "insufficient_evidence"
                         and isinstance(fields.get("verification"), dict)
                         and fields["verification"].get("level") == "unverified"
                         and "clarify_source_scope" in fields.get("selected_tools", [])
                         and "다시 질문:" in fields.get("answer", "")
                         and len(fields.get("evidence", [])) >= 2 and fields.get("confidence") == 0)
            if clarified:
                errors = []
            result = {"id": case["id"], "file": case["file"], "question": case["question"],
                      "http_status": response.status_code, "response": body,
                      "strict_answer_errors": strict_errors,
                      "outcome": "scope_clarification" if clarified else "answer",
                      "seconds": round(time.monotonic() - started, 2), "errors": errors}
        except Exception as error:
            result = {"id": case["id"], "file": case["file"], "question": case["question"],
                      "seconds": round(time.monotonic() - started, 2),
                      "errors": [f"{type(error).__name__}: {error}"]}
        fields = result.get("response")
        print(json.dumps({"id": result["id"], "errors": result["errors"],
                          "answer": fields.get("answer") if isinstance(fields, dict) else None,
                          "seconds": result["seconds"]}, ensure_ascii=False), flush=True)
        return result


async def main(args):
    cases = json.loads(args.cases.read_text())["cases"]
    if args.case:
        cases = [case for case in cases if case["id"] in args.case]
    if not cases:
        raise SystemExit("No evaluation cases selected")
    semaphore = asyncio.Semaphore(args.concurrency)
    async with httpx.AsyncClient(timeout=args.timeout) as client:
        results = await asyncio.gather(*[
            run_case(client, semaphore, case, args.directory, args.endpoint, args.allow_clarification) for case in cases
        ])
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "endpoint": args.endpoint,
              "case_count": len(results),
              "passed_pattern_checks": sum(not item.get("strict_answer_errors", item["errors"]) for item in results),
              "passed_behavior_checks": sum(not item["errors"] for item in results),
              "scope_clarifications": sum(item.get("outcome") == "scope_clarification" for item in results),
              "note": "Answer patterns and source coverage supplement, not replace, original-cell semantic review.",
              "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return all(not result["errors"] for result in results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/api/v1/workbooks/questions")
    parser.add_argument("--case", action="append")
    parser.add_argument("--allow-clarification", action="append", default=[],
                        help="Explicit case ID with independently confirmed ambiguous sources; retain strict-answer failures.")
    parser.add_argument("--concurrency", type=int, choices=range(1, 5), default=2)
    parser.add_argument("--timeout", type=float, default=180)
    raise SystemExit(0 if asyncio.run(main(parser.parse_args())) else 1)
