"""One manifest contract for online questions, conversations and offline runs.

These checks test declared expectations, not independent semantic correctness.
"""
import re

if __package__:
    from .evidence_checks import evidence_errors, source_ranges
else:  # Keep direct `python evals/run_questions.py` invocations working.
    from evidence_checks import evidence_errors, source_ranges


def check_response(case, status, body):
    errors = []
    if status != 200:
        errors.append(f"HTTP {status}")
    if not isinstance(body, dict):
        return [*errors, "Response body must be a JSON object"]
    expected_statuses = case.get("statuses") or ["answered"]
    if body.get("status") not in expected_statuses:
        errors.append(f"status={body.get('status')}")
    answer = body.get("answer", "")
    if not isinstance(answer, str):
        errors.append("Answer must be text")
        answer = ""
    for key, required in (("required_patterns", True), ("forbidden_patterns", False)):
        for pattern in case.get(key) or []:
            try:
                found = bool(re.search(pattern, answer, re.I))
            except (re.error, TypeError):
                errors.append(f"Invalid answer pattern: {pattern}")
                continue
            if found != required:
                errors.append(f"{'Missing' if required else 'Forbidden'} answer pattern: {pattern}")
    verification = body.get("verification") or {}
    if not isinstance(verification, dict):
        errors.append("Verification must be an object")
        verification = {}
    level = verification.get("level", "unverified")
    if level not in {"unverified", "source_checked", "request_checked"}:
        errors.append(f"Invalid verification: {level}")
    if case.get("verified") and level != "request_checked":
        errors.append("Request-bound verification missing")
    if case.get("verification_levels") and level not in case["verification_levels"]:
        errors.append(f"Unexpected verification: {level}")
    if case.get("forbid_request_checked") and level == "request_checked":
        errors.append("Unsupported request-level verification")
    evidence = body.get("evidence") or []
    if not isinstance(evidence, list):
        errors.append("Evidence must be a list")
        evidence = []
    if level in {"source_checked", "request_checked"} and not source_ranges(evidence):
        errors.append("Source-bound verification has no valid source references")
    errors.extend(evidence_errors(case.get("evidence_targets") or [], evidence))
    return errors
