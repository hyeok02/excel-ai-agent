"""An in-process production API with network and model generation disabled."""
from contextlib import asynccontextmanager

import httpx
from pytest import MonkeyPatch

from tests.support.offline_network import install_network_guard


class ModelRequired(BaseException):
    """Not caught by production fallback handlers; an unmet offline acceptance case."""


class NoModel:
    async def generate(self, *args, **kwargs):
        raise ModelRequired("This request requires model generation; no model was called.")


@asynccontextmanager
async def offline_client(classifier=None):
    # Install before importing API modules, including their environment initializers.
    with MonkeyPatch.context() as patch:
        install_network_guard(patch)
        from app.api import workbook_questions
        from app.main import app

        patch.setattr(workbook_questions, "_intent_classifier", classifier)
        patch.setattr(workbook_questions, "_context_resolver", None)
        patch.setitem(app.dependency_overrides,
                      workbook_questions.get_question_answer_generator, NoModel)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://offline"
        ) as client:
            yield client
