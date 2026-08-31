from app.agent.registry import AgentToolRegistry
from app.agent.tools import (
    CircularReferenceTool,
    FormulaDependencyTool,
    FormulaRiskTool,
    SemanticStructureTool,
    WorkbookDataSearchTool,
)


def create_default_tool_registry() -> AgentToolRegistry:
    return AgentToolRegistry(
        (
            WorkbookDataSearchTool(),
            SemanticStructureTool(),
            FormulaDependencyTool(),
            CircularReferenceTool(),
            FormulaRiskTool(),
        )
    )
