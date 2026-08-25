from collections import deque

from app.services.dependencies.models import (
    DependencyCluster,
    DependencyCycle,
    DependencyEdge,
    DependencyNode,
)

MAX_NODES_PER_CLUSTER = 18
MAX_EDGES_PER_CLUSTER = 28
MAX_NODES_PER_CYCLE = 12
MAX_EDGES_PER_CYCLE = 20


def summarize_cycle(
    display_index: int,
    component: set[str],
    all_nodes: dict[str, DependencyNode],
    all_edges: list[DependencyEdge],
) -> DependencyCycle:
    node_ids = sorted(component)
    sampled_node_ids = node_ids[:MAX_NODES_PER_CYCLE]
    sampled_node_set = set(sampled_node_ids)
    component_edges = [
        edge
        for edge in all_edges
        if edge.source in component and edge.target in component
    ]
    sampled_edges = [
        edge
        for edge in component_edges
        if edge.source in sampled_node_set and edge.target in sampled_node_set
    ][:MAX_EDGES_PER_CYCLE]
    return DependencyCycle(
        id=f"cycle-{display_index}",
        node_count=len(component),
        edge_count=len(component_edges),
        sheet_names=_sheet_names(component, all_nodes),
        nodes=[all_nodes[node_id] for node_id in sampled_node_ids],
        edges=sampled_edges,
        is_truncated=(
            len(component) > len(sampled_node_ids)
            or len(component_edges) > len(sampled_edges)
        ),
    )


def summarize_cluster(
    display_index: int,
    component: set[str],
    component_edges: list[DependencyEdge],
    all_nodes: dict[str, DependencyNode],
    adjacency: dict[str, set[str]],
) -> DependencyCluster:
    sampled_node_ids = sample_connected_nodes(component, adjacency)
    sampled_node_set = set(sampled_node_ids)
    sampled_edges = [
        edge
        for edge in component_edges
        if edge.source in sampled_node_set and edge.target in sampled_node_set
    ][:MAX_EDGES_PER_CLUSTER]
    return DependencyCluster(
        id=f"cluster-{display_index}",
        node_count=len(component),
        edge_count=len(component_edges),
        formula_count=sum(all_nodes[node_id].kind == "formula" for node_id in component),
        sheet_names=_sheet_names(component, all_nodes),
        nodes=[all_nodes[node_id] for node_id in sampled_node_ids],
        edges=sampled_edges,
        is_truncated=(
            len(component) > len(sampled_node_ids)
            or len(component_edges) > len(sampled_edges)
        ),
    )


def sample_connected_nodes(
    component: set[str],
    adjacency: dict[str, set[str]],
) -> list[str]:
    start_node = max(component, key=lambda node_id: (len(adjacency[node_id]), node_id))
    sampled: list[str] = []
    visited = {start_node}
    queue = deque([start_node])
    while queue and len(sampled) < MAX_NODES_PER_CLUSTER:
        node_id = queue.popleft()
        sampled.append(node_id)
        neighbors = sorted(
            adjacency[node_id],
            key=lambda neighbor: (len(adjacency[neighbor]), neighbor),
            reverse=True,
        )
        for neighbor in neighbors:
            if neighbor in component and neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return sampled


def _sheet_names(
    component: set[str],
    nodes: dict[str, DependencyNode],
) -> list[str]:
    return sorted(
        {nodes[node_id].sheet for node_id in component if nodes[node_id].sheet is not None}
    )
