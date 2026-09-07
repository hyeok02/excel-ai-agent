"""Check that cited row labels stay attached to their own values."""
import re
from collections import defaultdict

from app.agent.query.search_terms import search_terms
from app.services.insights.numeric_validation import numbers, unmatched_numbers

CELL = re.compile(r"^([A-Z]+)(\d+)$", re.I)
CLAUSE = re.compile(r"[.!?;\n]|,\s*|\b(?:and|while)\b|(?:이고|이며|반면|그리고)", re.I)


def answer_bindings_supported(answer: str, evidence: list[object]) -> bool:
    rows = _labeled_numeric_rows(evidence)
    if len(rows) < 2:
        return True
    for clause in CLAUSE.split(answer):
        clause_terms = set(search_terms(clause))
        clause_values = numbers(clause)
        if not clause_values:
            continue
        for labels, values in rows.values():
            if not any(_mentioned(value, clause_values) for value in values):
                continue
            label_terms = {term for label in labels for term in search_terms(label)}
            if label_terms and not label_terms & clause_terms:
                return False
    return True


def _labeled_numeric_rows(evidence: list[object]):
    grouped = defaultdict(lambda: ([], []))
    for item in evidence:
        reference = getattr(item, "reference", "") or ""
        match = CELL.fullmatch(reference.replace("$", ""))
        sheet = getattr(item, "sheet_name", "")
        if not match or not sheet:
            continue
        labels, values = grouped[(sheet.casefold(), int(match.group(2)))]
        value = getattr(item, "value", None)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(value)
        elif isinstance(value, str) and value.strip():
            labels.append(value)
    return {
        key: (labels, values)
        for key, (labels, values) in grouped.items()
        if labels and values
    }


def _mentioned(value: object, clause_values) -> bool:
    return not unmatched_numbers(str(value), clause_values)
