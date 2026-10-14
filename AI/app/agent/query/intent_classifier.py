"""질문 의도를 모델이 고른다.

낱말 목록으로 의도를 고르면 같은 질문도 표현이 조금만 달라지면 빗나간다.
'이 파일은 뭐에 관련된 얘기야?'가 목록에 없어 요약 경로가 꺼지고, 검색이
'관련된', '얘기야'로 엉뚱한 행을 가져와 답변이 "근거 부족"으로 나갔다.

고르는 일만 모델에게 맡기고, 계산과 셀 선택은 코드가 그대로 한다. 모델이
틀리거나 부르지 못해도 아래 단계가 받아내도록 결과는 게이트가 아니라
순위 힌트로만 쓴다.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agent.query.intent_models import (
    QuestionIntent,
    QuestionIntentDraft,
)
from app.agent.query.intent_prompts import SYSTEM_PROMPT, build_intent_prompt
from app.services.workbook_parsing.models import WorkbookSummary

DEFAULT_MODEL = "gpt-4.1-nano"
DEFAULT_TIMEOUT = 8.0
MAX_CACHED = 128


class LangChainQuestionIntentClassifier:
    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._cache: dict[tuple[str, str], QuestionIntent] = {}

    @classmethod
    def from_environment(cls) -> "LangChainQuestionIntentClassifier | None":
        """키가 없으면 분류기 없이 돌린다. 낱말 규칙이 대신한다."""
        load_dotenv(Path(__file__).resolve().parents[3] / ".env")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "replace-with-your-api-key":
            return None
        model = (
            os.getenv("OPENAI_INTENT_MODEL")
            or os.getenv("OPENAI_FAST_MODEL")
            or DEFAULT_MODEL
        )
        return cls(api_key, model, _timeout())

    async def classify(
        self, question: str, summary: WorkbookSummary
    ) -> QuestionIntent:
        key = (summary.filename, question.strip())
        if found := self._cache.get(key):
            return found
        try:
            result = await self._build_model().ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=build_intent_prompt(question, summary)),
                ]
            )
            intent = QuestionIntent.from_draft(
                QuestionIntentDraft.model_validate(result)
            )
        except Exception:
            # 분류에 실패했다고 질문에 답하지 못할 이유는 없다.
            return QuestionIntent.from_keywords(question)
        if len(self._cache) < MAX_CACHED:
            self._cache[key] = intent
        return intent

    def _build_model(self):
        return ChatOpenAI(
            model=self._model,
            api_key=self._api_key,
            timeout=self._timeout_seconds,
            max_retries=1,
            max_completion_tokens=200,
        ).with_structured_output(QuestionIntentDraft, method="json_schema")


def _timeout() -> float:
    try:
        return float(os.getenv("OPENAI_INTENT_TIMEOUT_SECONDS", DEFAULT_TIMEOUT))
    except ValueError:
        return DEFAULT_TIMEOUT
