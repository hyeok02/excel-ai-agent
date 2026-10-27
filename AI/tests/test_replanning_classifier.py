import asyncio

from app.agent.query.intent_classifier import LangChainQuestionIntentClassifier
from tests.test_intent_classifier_cache import _summary


class Model:
    def __init__(self):
        self.messages = []

    async def ainvoke(self, messages):
        self.messages.append(messages)
        return {"scope": "specific", "kind": "aggregation", "tabular_query": {
            "operation": "numeric_summary", "table_id": "Records!A1:B4",
            "column_ids": ["B"], "statistic": "sum"}}


def test_repair_cache_is_scoped_to_diagnostic_question_and_source_catalog():
    model = Model()
    planner = LangChainQuestionIntentClassifier("unused", "unused", 1)
    planner._build_model = lambda: model
    summary = _summary("same.xlsx", "Records")
    feedback = {"code": "unknown_table_id", "previous_plan": {"table_id": "invented"}}

    async def repair():
        a = await planner.replan("Amount 합계", summary, feedback)
        b = await planner.replan("Amount 합계", summary, feedback)
        await planner.replan("Amount 합계", _summary("same.xlsx", "Other"), feedback)
        await planner.replan("Amount 평균", summary, feedback)
        await planner.replan("Amount 합계", summary, {**feedback, "code": "other_failure"})
        assert a == b

    asyncio.run(repair())
    assert len(model.messages) == 4
    assert "원래 질문" in model.messages[0][0].content
    assert "unknown_table_id" in model.messages[0][1].content


def test_repair_provider_or_schema_failure_does_not_create_keyword_plan():
    planner = LangChainQuestionIntentClassifier("unused", "unused", 1)

    class Invalid:
        async def ainvoke(self, messages):
            return {"not_a_plan": "do not trust"}

    planner._build_model = lambda: Invalid()
    assert asyncio.run(planner.replan("Amount 합계", _summary("a.xlsx", "A"), {})) is None
