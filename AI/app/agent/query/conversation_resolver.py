"""Optional, bounded resolution call using the configured intent model."""
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import Field, create_model

from app.agent.query.conversation_models import ContextResolutionDraft
from app.agent.query.conversation_prompt import SYSTEM_PROMPT, resolution_prompt
from app.agent.query.intent_classifier import DEFAULT_MODEL, _timeout


class LangChainQuestionContextResolver:
    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        self._api_key, self._model, self._timeout = api_key, model, timeout_seconds

    @classmethod
    def from_environment(cls):
        load_dotenv(Path(__file__).resolve().parents[3] / ".env")
        key = os.getenv("OPENAI_API_KEY")
        if not key or key == "replace-with-your-api-key":
            return None
        model = os.getenv("OPENAI_INTENT_MODEL") or os.getenv("OPENAI_QA_MODEL") or DEFAULT_MODEL
        return cls(key, model, min(_timeout(), 20.0))

    def _build_model(self, ids):
        allowed = Literal[tuple(ids)]
        schema = create_model(
            "BoundContextResolution", __base__=ContextResolutionDraft,
            context_ids=(list[allowed], Field(default_factory=list, max_length=6,
                                              description="Only the provided turn/insight IDs, not cell addresses")),
        )
        return ChatOpenAI(
            model=self._model, api_key=self._api_key, timeout=self._timeout,
            max_retries=0, max_completion_tokens=900,
        ).with_structured_output(schema, method="json_schema")

    async def resolve(self, question: str, context: list[dict]) -> ContextResolutionDraft:
        result = await self._build_model([entry["id"] for entry in context]).ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=resolution_prompt(question, context)),
        ])
        return ContextResolutionDraft.model_validate(result)
