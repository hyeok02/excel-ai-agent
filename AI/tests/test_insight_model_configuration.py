from app.services.analysis_strategy import FAST_PROFILE, STANDARD_PROFILE
from app.services.insights.generator import LangChainInsightGenerator


def test_fast_uses_available_nonreasoning_model_with_fast_output_budget(monkeypatch):
    options = {}

    class Model:
        def __init__(self, **kwargs):
            options.update(kwargs)

        def with_structured_output(self, *_args, **_kwargs):
            return self

    monkeypatch.delenv("OPENAI_FAST_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "custom-standard")
    monkeypatch.setattr("app.services.insights.generator.ChatOpenAI", Model)
    generator = LangChainInsightGenerator("unused", 10, "minimal")
    generator._build_model(FAST_PROFILE)
    assert options["model"] == "gpt-4.1-mini"
    assert options["max_completion_tokens"] == FAST_PROFILE.max_completion_tokens
    assert "reasoning_effort" not in options

    monkeypatch.setenv("OPENAI_FAST_MODEL", "custom-fast")
    generator._build_model(FAST_PROFILE)
    assert options["model"] == "custom-fast"
    monkeypatch.delenv("OPENAI_STANDARD_MODEL", raising=False)
    generator._build_model(STANDARD_PROFILE)
    assert options["model"] == "custom-standard"
