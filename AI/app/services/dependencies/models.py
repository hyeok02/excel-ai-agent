from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyNode:
    id: str
    label: str
    sheet: str | None
    cell: str | None
    kind: str
    formula: str | None


@dataclass(frozen=True)
class DependencyEdge:
    source: str
    target: str
    reference: str
    cross_sheet: bool


@dataclass(frozen=True)
class DependencyCluster:
    id: str
    node_count: int
    edge_count: int
    formula_count: int
    sheet_names: list[str]
    nodes: list[DependencyNode]
    edges: list[DependencyEdge]
    is_truncated: bool


@dataclass(frozen=True)
class DependencyCycle:
    id: str
    node_count: int
    edge_count: int
    sheet_names: list[str]
    nodes: list[DependencyNode]
    edges: list[DependencyEdge]
    is_truncated: bool


@dataclass(frozen=True)
class DependencySummary:
    node_count: int
    edge_count: int
    formula_node_count: int
    cross_sheet_edge_count: int
    named_reference_count: int
    external_reference_count: int
    cluster_count: int
    clusters: list[DependencyCluster]
    cycle_count: int
    cyclic_node_count: int
    cycles: list[DependencyCycle]

    @classmethod
    def empty(cls) -> "DependencySummary":
        return cls(0, 0, 0, 0, 0, 0, 0, [], 0, 0, [])
