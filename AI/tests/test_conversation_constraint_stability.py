"""A context rewrite must not reverse explicit numeric filter conditions."""
import pytest

from app.agent.query.conversation_checks import resolution_is_safe
from app.agent.query.conversation_models import ContextResolutionDraft


def safe(original, rewritten):
    context = [{"id": "turn:0", "hint": {"question": "Amount 값은?"}, "source_cells": [
        {"reference": "Records!B1", "value": "Amount"},
        {"reference": "Records!B2", "value": 10},
    ]}]
    draft = ContextResolutionDraft(status="resolved", question=rewritten, context_ids=["turn:0"])
    return resolution_is_safe(original, draft, context)


@pytest.mark.parametrize("original,rewritten", [
    ("그중 Amount > 10인 항목은?", "Records에서 Amount < 10인 항목은?"),
    ("그중 Amount >= 10인 항목은?", "Records에서 Amount > 10인 항목은?"),
    ("그중 Amount != 10인 항목은?", "Records에서 Amount = 10인 항목은?"),
    ("그중 Amount ≤ 10인 항목은?", "Records에서 Amount ≥ 10인 항목은?"),
    ("그중 Amount -10인 항목은?", "Records에서 Amount 10인 항목은?"),
    ("그중 Amount 10인 항목은?", "Records에서 Amount -10인 항목은?"),
    ("그중 Amount > -10인 항목은?", "Records에서 Amount > 10인 항목은?"),
    ("그중 10 < Amount 항목은?", "Records에서 10 > Amount 항목은?"),
    ("그중 10 < Amount < 20인 항목은?", "Records에서 10 < Amount > 20인 항목은?"),
])
def test_rejects_changed_comparison_operator_or_sign(original, rewritten):
    assert not safe(original, rewritten)


@pytest.mark.parametrize("original,rewritten", [
    ("그중 Amount > 10인 항목은?", "Records에서 Amount > 10인 항목은?"),
    ("그중 Amount ≥ 10인 항목은?", "Records에서 Amount >= 10인 항목은?"),
    ("그중 Amount != -10인 항목은?", "Records에서 Amount ≠ -10인 항목은?"),
    ("그중 Amount > 10인 항목은?", "Records에서 Amount 10 초과인 항목은?"),
    ("그중 Amount >= 10인 항목은?", "Records에서 Amount at least 10인 항목은?"),
    ("그중 10 < Amount 항목은?", "Records에서 Amount > 10 항목은?"),
    ("그중 2024-01-31 Amount 값은?", "Records에서 2024-01-31 Amount 값은?"),
])
def test_preserves_equivalent_symbols_and_does_not_treat_dates_as_negatives(original, rewritten):
    assert safe(original, rewritten)
