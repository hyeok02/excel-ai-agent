"""Keep API unit tests independent of a developer's configured live model.

Tests supply answer generators and exercise deterministic fallback routing.
Classifier tests inject their own models; evals/run_questions.py separately
exercises the actual HTTP service with its live intent classifier.
"""
import pytest

from tests.support.offline_network import install_network_guard


def pytest_configure(config):
    """Protect collection, fixtures and tests, even with a real key in .env."""
    guard = pytest.MonkeyPatch()
    install_network_guard(guard)
    config.add_cleanup(guard.undo)


@pytest.fixture(autouse=True)
def offline_api_intent_classifier(monkeypatch):
    monkeypatch.setattr("app.api.workbook_questions._intent_classifier", None)
    monkeypatch.setattr("app.api.workbook_questions._context_resolver", None)
