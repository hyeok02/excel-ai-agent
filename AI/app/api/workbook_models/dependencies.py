from pydantic import BaseModel, ConfigDict


class DependencyNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    label: str
    sheet: str | None
    cell: str | None
    kind: str
    formula: str | None


class DependencyEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source: str
    target: str
    reference: str
    cross_sheet: bool


class DependencyClusterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    node_count: int
    edge_count: int
    formula_count: int
    sheet_names: list[str]
    nodes: list[DependencyNodeResponse]
    edges: list[DependencyEdgeResponse]
    is_truncated: bool


class DependencyCycleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    node_count: int
    edge_count: int
    sheet_names: list[str]
    nodes: list[DependencyNodeResponse]
    edges: list[DependencyEdgeResponse]
    is_truncated: bool


class DependencySummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    node_count: int
    edge_count: int
    formula_node_count: int
    cross_sheet_edge_count: int
    named_reference_count: int
    external_reference_count: int
    cluster_count: int
    clusters: list[DependencyClusterResponse]
    cycle_count: int
    cyclic_node_count: int
    cycles: list[DependencyCycleResponse]
