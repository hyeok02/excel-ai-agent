"""Strict real-file acceptance without live models, HTTP servers or file edits."""
import argparse
import asyncio
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from evals.offline_api import ModelRequired, offline_client
from evals.run_conversations import check_response, request_context
from evals.run_questions import evidence_errors
from tests.support.offline_network import ExternalNetworkForbidden


def check_case(case, status, body):
    errors = check_response({"statuses": ["answered"], **case}, status, body)
    errors.extend(evidence_errors(case.get("evidence_targets", []), body.get("evidence", [])))
    level = body.get("verification", {}).get("level", "unverified")
    if case.get("verified") and level != "request_checked":
        errors.append("Request-bound verification missing")
    if case.get("verification_levels") and level not in case["verification_levels"]:
        errors.append(f"Unexpected verification: {level}")
    return errors


def validate_cases(cases):
    seen = {}
    if not cases:
        raise ValueError("No acceptance cases selected")
    for case in cases:
        if case["id"] in seen:
            raise ValueError(f"Duplicate case: {case['id']}")
        parent = case.get("parent")
        if parent and (parent not in seen or seen[parent] != case["file"]):
            raise ValueError(f"Parent must precede child in the same file: {case['id']}")
        if not case.get("question") or not case.get("required_patterns"):
            raise ValueError(f"A question and independent expected answer patterns are required: {case['id']}")
        seen[case["id"]] = case["file"]


async def run(cases, paths):
    validate_cases(cases)
    contents = {name: path.read_bytes() for name, path in paths.items()}
    digests = {name: sha256(content).hexdigest() for name, content in contents.items()}
    results = {}
    async with offline_client() as client:
        for case in cases:
            previous = results.get(case.get("parent"))
            context = request_context(case, previous)
            record = {"id": case["id"], "file": case["file"], "question": case["question"],
                      "sent_context": context}
            if previous and previous.get("outcome") in ("model_required", "parent_unavailable"):
                record.update(outcome="parent_unavailable", errors=["Parent was not evaluated"])
            else:
                try:
                    response = await client.post("/api/v1/workbooks/questions",
                        data={"question": case["question"], "context": json.dumps(context)},
                        files={"file": (case["file"], contents[case["file"]])})
                    body = response.json()
                    record.update(http_status=response.status_code, response=body,
                                  outcome=body.get("status", "http_error"),
                                  errors=check_case(case, response.status_code, body))
                except ModelRequired as error:
                    record.update(outcome="model_required", errors=[str(error)])
                except ExternalNetworkForbidden as error:
                    record.update(outcome="network_attempt_blocked", errors=[str(error)])
                except Exception as error:
                    record.update(outcome="execution_error", errors=[f"{type(error).__name__}: {error}"])
            results[case["id"]] = record
            print(json.dumps({key: record[key] for key in ("id", "outcome", "errors")},
                             ensure_ascii=False), flush=True)
    unchanged = all(sha256(paths[name].read_bytes()).hexdigest() == digest
                    for name, digest in digests.items())
    return {"created_at": datetime.now(timezone.utc).isoformat(), "network_blocked": True,
            "paid_calls": 0, "originals_unchanged": unchanged, "source_sha256": digests,
            "scope": "offline_deterministic_api_only; live model interpretation is not evaluated",
            "case_count": len(results), "passed": sum(not r["errors"] for r in results.values()),
            "outcomes": {outcome: sum(r["outcome"] == outcome for r in results.values())
                         for outcome in sorted({r["outcome"] for r in results.values()})},
            "accepted": unchanged and all(not r["errors"] for r in results.values()),
            "results": list(results.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--directory", type=Path, default=Path("."))
    parser.add_argument("--file-map", type=Path, help="Local JSON: {files: {filename: {path: ...}}}")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text())["cases"]
    file_map = json.loads(args.file_map.read_text())["files"] if args.file_map else {}
    paths = {case["file"]: Path(file_map[case["file"]]["path"])
             if case["file"] in file_map else args.directory / case["file"] for case in cases}
    if args.output.resolve() in {path.resolve() for path in paths.values()}:
        raise ValueError("The report must not overwrite a source workbook")
    report = asyncio.run(run(cases, paths))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Accepted {report['passed']}/{report['case_count']}; report: {args.output}")
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
