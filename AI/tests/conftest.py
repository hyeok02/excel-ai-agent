"""Keep API unit tests independent of a developer's configured live model.

Tests supply answer generators and exercise deterministic fallback routing.
Classifier tests inject their own models; evals/run_questions.py separately
exercises the actual HTTP service with its live intent classifier.
"""
import pytest


@pytest.fixture(autouse=True)
def offline_api_intent_classifier(monkeypatch):
    monkeypatch.setattr("app.api.workbook_questions._intent_classifier", None)
    monkeypatch.setattr("app.api.workbook_questions._context_resolver", None)
