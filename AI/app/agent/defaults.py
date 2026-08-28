from app.agent.registry import AgentToolRegistry
from app.agent.tools import (
    CircularReferenceTool,
    FormulaDependencyTool,
    FormulaRiskTool,
    SemanticStructureTool,
)


def create_default_tool_registry() -> AgentToolRegistry:
    return AgentToolRegistry(
        (
            SemanticStructureTool(),
            FormulaDependencyTool(),
            CircularReferenceTool(),
            FormulaRiskTool(),
        )
    )
