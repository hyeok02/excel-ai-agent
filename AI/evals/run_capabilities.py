"""Exercise real classifier/API responses using in-memory regression workbooks."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import httpx

from capability_cases import capability_cases


async def main(args):
    results = []
    async with httpx.AsyncClient(timeout=180) as client:
        for name, content, question, status, patterns, level in capability_cases():
            errors = []
            try:
                response = await client.post(args.endpoint, data={"question": question},
                                             files={"file": (f"{name}.xlsx", content)})
                code = response.status_code
                body = response.json()
            except (httpx.HTTPError, ValueError) as error:
                code, body = 0, {}
                errors.append(f"{type(error).__name__}: {error}")
            if code != 200 or body.get("status") != status:
                errors.append(f"Expected HTTP200/{status}, got {code}/{body.get('status')}")
            for pattern in patterns:
                if not re.search(pattern, body.get("answer", "")):
                    errors.append(f"Missing pattern: {pattern}")
            if body.get("verification", {}).get("level") != level:
                errors.append(f"Expected verification: {level}")
            if name.startswith("formula_") and status == "limited" and not any(
                    "재계산" in item for item in body.get("limitations", [])):
                errors.append("Formula derivation provenance missing")
            results.append({"id": name, "question": question, "response": body, "errors": errors})
            print(json.dumps({"id": name, "errors": errors, "answer": body.get("answer")}, ensure_ascii=False), flush=True)
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "case_count": len(results),
              "passed_checks": sum(not item["errors"] for item in results), "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report["passed_checks"] == len(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/api/v1/workbooks/questions")
    raise SystemExit(0 if asyncio.run(main(parser.parse_args())) else 1)
