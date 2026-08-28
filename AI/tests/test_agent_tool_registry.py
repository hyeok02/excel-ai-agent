from pathlib import Path

import pytest

from app.agent import (
    AgentToolContext,
    AgentToolRegistry,
    ToolNotFoundError,
    create_default_tool_registry,
)
from app.agent.tools import SemanticStructureTool
from app.services.workbook_parser import parse_workbook


def test_default_registry_exposes_existing_analysis_capabilities() -> None:
    registry = create_default_tool_registry()

    assert [metadata.name for metadata in registry.list_metadata()] == [
        "inspect_semantic_structure",
        "trace_formula_dependencies",
        "detect_circular_references",
        "assess_formula_risks",
    ]


def test_registry_rejects_duplicate_and_unknown_tools() -> None:
    registry = AgentToolRegistry((SemanticStructureTool(),))

    with pytest.raises(ValueError, match="이미 등록된"):
        registry.register(SemanticStructureTool())
    with pytest.raises(ToolNotFoundError, match="등록되지 않은"):
        registry.get("unknown")


def test_registered_tools_execute_against_one_workbook_context() -> None:
    fixture = Path(__file__).parent / "fixtures/semantic/semantic_mixed_regions.xlsx"
    with open(fixture, "rb") as workbook_file:
        summary = parse_workbook(fixture.name, workbook_file.read())
    context = AgentToolContext(summary)
    registry = create_default_tool_registry()

    semantic = registry.execute("inspect_semantic_structure", context)
    dependencies = registry.execute("trace_formula_dependencies", context)
    cycles = registry.execute("detect_circular_references", context)
    risks = registry.execute("assess_formula_risks", context)

    assert semantic.data["sheets"]
    assert dependencies.data["cluster_count"] >= 0
    assert cycles.data["cycle_count"] >= 0
    assert risks.data["total_count"] >= 0
