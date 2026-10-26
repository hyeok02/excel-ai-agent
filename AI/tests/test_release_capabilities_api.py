"""API executor acceptance with fixed planner proposals, not live-model accuracy."""
import asyncio
import re

import pytest

from evals.capability_cases import capability_cases
from evals.offline_api import offline_client
from tests.support.release_capability_plans import CapabilityPlanner


@pytest.mark.parametrize("case", capability_cases(), ids=lambda case: case[0])
def test_validated_capability_plans_through_real_api(case):
    name, content, question, status, patterns, level = case

    async def request():
        async with offline_client(CapabilityPlanner(name)) as client:
            return await client.post("/api/v1/workbooks/questions", data={"question": question},
                                     files={"file": (f"{name}.xlsx", content)})
    response = asyncio.run(request())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == status, body
    assert body["verification"]["level"] == level, body
    for pattern in patterns:
        assert re.search(pattern, body["answer"]), body
    if status != "insufficient_evidence":
        assert body["evidence"], body
    if name.startswith("formula_") and status == "limited":
        assert any("재계산" in item for item in body["limitations"]), body
