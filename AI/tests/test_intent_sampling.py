"""The question interpreter asks for the most likely plan, not a sampled one."""
from app.agent.query.intent_classifier import _sampling


def test_plans_are_requested_without_sampling_by_default(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_INTENT_TEMPERATURE", raising=False)
    assert _sampling() == {"temperature": 0.0}


def test_an_empty_setting_omits_temperature_for_models_that_reject_it(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_INTENT_TEMPERATURE", "")
    assert _sampling() == {}
    monkeypatch.setenv("OPENAI_INTENT_TEMPERATURE", "0.2")
    assert _sampling() == {"temperature": 0.2}
