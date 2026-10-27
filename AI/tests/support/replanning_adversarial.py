"""Real service execution with deterministic planners; no generation or network."""
import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.service import WorkbookQuestionService
from tests.support.offline_network import ExternalNetworkForbidden, install_network_guard


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    install_network_guard(monkeypatch)


class NoGeneration:
    async def generate(self, *args, **kwargs):
        raise ExternalNetworkForbidden("A repaired plan cannot use generated fallback answers")


class Planner:
    def __init__(self, first, revised):
        self.first, self.revised = first, revised
        self.questions, self.repairs = [], []

    async def classify(self, question, summary):
        self.questions.append(question)
        return self.first

    async def replan(self, question, summary, feedback):
        self.repairs.append((question, feedback))
        if isinstance(self.revised, Exception):
            raise self.revised
        return self.revised


def intent(plan, **kwargs):
    return QuestionIntent(False, "aggregation", from_model=True, tabular_query=plan, **kwargs)


def run(question, summary, index, planner):
    service = WorkbookQuestionService(NoGeneration(), create_default_tool_registry(), classifier=planner)
    return asyncio.run(service.answer(question, summary, index))


def rejected(answer):
    assert answer.status == "insufficient_evidence", answer.model_dump()
    assert answer.verification.level != "request_checked", answer.model_dump()
    assert "plan_replanned" not in answer.verification.checks


def repaired(answer, planner, question):
    assert answer.status == "answered", answer.model_dump()
    assert answer.verification.level == "request_checked", answer.model_dump()
    assert {"request_alignment", "plan_replanned"} <= set(answer.verification.checks)
    assert answer.evidence
    assert planner.questions == [question]
    assert len(planner.repairs) == 1 and planner.repairs[0][0] == question
