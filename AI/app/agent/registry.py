from collections.abc import Iterable

from app.agent.contracts import (
    AgentTool,
    AgentToolContext,
    AgentToolMetadata,
    AgentToolResult,
    ToolArguments,
)


class ToolNotFoundError(LookupError):
    """Raised when a requested Agent Tool is not registered."""


class AgentToolRegistry:
    def __init__(self, tools: Iterable[AgentTool] = ()) -> None:
        self._tools: dict[str, AgentTool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: AgentTool) -> None:
        name = tool.metadata.name
        if name in self._tools:
            raise ValueError(f"이미 등록된 Agent Tool입니다: {name}")
        self._tools[name] = tool

    def get(self, name: str) -> AgentTool:
        try:
            return self._tools[name]
        except KeyError as exception:
            raise ToolNotFoundError(f"등록되지 않은 Agent Tool입니다: {name}") from exception

    def list_metadata(self) -> tuple[AgentToolMetadata, ...]:
        return tuple(tool.metadata for tool in self._tools.values())

    def execute(
        self,
        name: str,
        context: AgentToolContext,
        arguments: ToolArguments | None = None,
    ) -> AgentToolResult:
        return self.get(name).execute(context, arguments)

    def __len__(self) -> int:
        return len(self._tools)
