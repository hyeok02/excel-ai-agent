"""Replay real workbook questions using actual earlier responses as context.

Expected answers belong to manifests only. The application never reads these
fixtures. Pattern checks supplement independent source-cell review, not replace it.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time

import httpx


def context_turn(result):
    body = result.get("response", {})
    references = []
    for item in body.get("evidence", []):
        sheet = item.get("sheet_name", "").replace("'", "''")
        address = item.get("reference", "").replace("$", "").upper()
        if not re.fullmatch(r"[A-Z]{1,3}[1-9]\d*(?::[A-Z]{1,3}[1-9]\d*)?", address):
            continue
        reference = f"'{sheet}'!{address}"
        if sheet and reference not in references and len(reference) <= 200:
            references.append(reference)
    turn = {"question": body.get("resolved_question") or result["question"],
            "evidence": references[:12]}
    if body.get("status") == "insufficient_evidence":
        turn["needs_clarification"] = True
    return turn


def check_response(case, status, body):
    errors = []
    if status != 200:
        errors.append(f"HTTP {status}")
    if case.get("statuses") and body.get("status") not in case["statuses"]:
        errors.append(f"status={body.get('status')}")
    for pattern in case.get("required_patterns") or []:
        if not re.search(pattern, body.get("answer", ""), re.I):
            errors.append(f"Missing answer pattern: {pattern}")
    for pattern in case.get("forbidden_patterns") or []:
        if re.search(pattern, body.get("answer", ""), re.I):
            errors.append(f"Forbidden answer pattern: {pattern}")
    if case.get("forbid_request_checked") and body.get("verification", {}).get("level") == "request_checked":
        errors.append("Unsupported request-level verification")
    return errors


def request_context(case, previous=None):
    prior = previous["sent_context"] if previous else {"turns": [], "insights": []}
    history = [*prior["turns"], context_turn(previous)][-6:] if previous else []
    return {"turns": history, "insights": case.get("insights", prior["insights"])}


async def main(args):
    manifest = json.loads(args.cases.read_text())
    cases = manifest["cases"]
    if args.case:
        wanted = set(args.case)
        while parents := {c["parent"] for c in cases if c["id"] in wanted
                          and c.get("parent") and c["parent"] not in wanted}:
            wanted.update(parents)
        cases = [c for c in cases if c["id"] in wanted]
    if not cases:
        raise SystemExit("No cases selected")
    file_map = json.loads(args.file_map.read_text())["files"] if args.file_map else {}
    contents, metadata = {}, {}
    for name in dict.fromkeys(c["file"] for c in cases):
        path = Path(file_map[name]["path"]) if name in file_map else args.directory / name
        content = path.read_bytes()
        contents[name] = content
        metadata[name] = {"path": str(path.resolve()), "size": len(content),
                          "sha256": hashlib.sha256(content).hexdigest()}
    results, tasks = [], {}
    semaphore = asyncio.Semaphore(args.concurrency)
    created_at = datetime.now(timezone.utc).isoformat()

    async def run(client, case):
        previous = await tasks[case["parent"]] if case.get("parent") else None
        context = request_context(case, previous)
        record = {**case, "sent_context": context}
        async with semaphore:
            started = time.monotonic()
            try:
                data = {"question": case["question"]}
                if context["turns"] or context["insights"]:
                    data["context"] = json.dumps(context, ensure_ascii=False)
                response = await client.post(args.endpoint, data=data,
                    files={"file": (case["file"], contents[case["file"]])})
                body = response.json()
                record.update(http_status=response.status_code, response=body)
                record["errors"] = check_response(case, response.status_code, body)
            except Exception as exc:
                record["errors"] = [f"{type(exc).__name__}: {exc}"]
            record["seconds"] = round(time.monotonic() - started, 2)
        results.append(record)
        report = {"created_at": created_at, "endpoint": args.endpoint, "files": metadata,
                  "cases": len(cases), "completed": len(results), "results": results,
                  "note": "No automatic semantic-pass claim; review source values, scope, context and badges independently."}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        body = record.get("response", {})
        print(json.dumps({"id": case["id"], "seconds": record["seconds"],
                          "errors": record["errors"], "status": body.get("status"),
                          "answer": body.get("answer"), "resolved": body.get("resolved_question"),
                          "verification": body.get("verification")},
                         ensure_ascii=False), flush=True)
        return record

    async with httpx.AsyncClient(timeout=args.timeout) as client:
        for case in cases:
            if case.get("parent") and case["parent"] not in tasks:
                raise ValueError(f"Parent must precede child: {case['id']}")
            tasks[case["id"]] = asyncio.create_task(run(client, case))
        await asyncio.gather(*tasks.values())
    return not any(r["errors"] for r in results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--file-map", type=Path)
    parser.add_argument("--directory", type=Path, default=Path("."))
    parser.add_argument("--case", action="append")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/api/v1/workbooks/questions")
    parser.add_argument("--concurrency", type=int, choices=range(1, 4), default=1)
    parser.add_argument("--timeout", type=float, default=180)
    raise SystemExit(0 if asyncio.run(main(parser.parse_args())) else 1)
