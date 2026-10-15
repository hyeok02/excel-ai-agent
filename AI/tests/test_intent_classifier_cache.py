import asyncio

from app.agent.query.intent_classifier import LangChainQuestionIntentClassifier
from app.services.workbook_parsing.models import SheetSummary, WorkbookSummary


class _CountingModel:
    def __init__(self) -> None:
        self.calls = 0

    async def ainvoke(self, _messages):
        self.calls += 1
        return {
            "scope": "specific",
            "kind": "cell_lookup",
            "targets": ["Amount"],
        }


class _Classifier(LangChainQuestionIntentClassifier):
    def __init__(self, model) -> None:
        super().__init__("test-key", "test-model", 1.0)
        self.model = model

    def _build_model(self):
        return self.model


def test_cache_is_scoped_to_workbook_structure_not_just_filename() -> None:
    model = _CountingModel()
    classifier = _Classifier(model)
    sales = _summary("report.xlsx", "Sales")
    inventory = _summary("report.xlsx", "Inventory")

    async def classify_all():
        await classifier.classify("금액 알려줘", sales)
        await classifier.classify("금액 알려줘", inventory)
        await classifier.classify("금액 알려줘", sales)

    asyncio.run(classify_all())

    assert model.calls == 2


def test_query_planning_uses_answer_model_unless_explicitly_overridden(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_QA_MODEL", "configured-answer-model")
    monkeypatch.setenv("OPENAI_FAST_MODEL", "lightweight-label-model")
    monkeypatch.delenv("OPENAI_INTENT_MODEL", raising=False)
    assert LangChainQuestionIntentClassifier.from_environment()._model == "configured-answer-model"
    monkeypatch.setenv("OPENAI_INTENT_MODEL", "explicit-planner-model")
    assert LangChainQuestionIntentClassifier.from_environment()._model == "explicit-planner-model"


def _summary(filename: str, sheet_name: str) -> WorkbookSummary:
    sheet = SheetSummary(
        name=sheet_name,
        rows=0,
        columns=0,
        formula_count=0,
        table_count=0,
        chart_count=0,
        formulas=[],
        region_count=0,
        regions=[],
    )
    return WorkbookSummary(filename, 1, [sheet])
