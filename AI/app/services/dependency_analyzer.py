from collections import defaultdict

from app.services.dependencies.graph import (
    connected_components,
    strongly_connected_components,
)
from app.services.dependencies.models import (
    DependencyEdge,
    DependencyNode,
    DependencySummary,
)
from app.services.dependencies.references import (
    cell_id,
    expand_range_formula_edges,
    normalize_address,
    reference_node,
)
from app.services.dependencies.summaries import summarize_cluster, summarize_cycle
from app.services.formula_analyzer import FormulaAnalysis

MAX_CLUSTERS = 8
MAX_CYCLES = 20


def analyze_dependencies(
    sheet_formulas: list[tuple[str, list[FormulaAnalysis]]],
) -> DependencySummary:
    nodes, edges = _build_graph(sheet_formulas)
    cycle_edges = expand_range_formula_edges(nodes, edges)
    directed, undirected = _adjacency(nodes, edges, cycle_edges)
    components = connected_components(undirected)
    edges_by_component = _edges_by_component(components, edges)
    ranked = sorted(
        enumerate(components),
        key=lambda item: (len(edges_by_component[item[0]]), len(item[1])),
        reverse=True,
    )
    clusters = [
        summarize_cluster(index, component, edges_by_component[position], nodes, undirected)
        for index, (position, component) in enumerate(ranked[:MAX_CLUSTERS], start=1)
    ]
    cycle_components = [
        component
        for component in strongly_connected_components(directed)
        if len(component) > 1
        or any(node_id in directed[node_id] for node_id in component)
    ]
    ranked_cycles = sorted(
        cycle_components, key=lambda component: (-len(component), sorted(component))
    )
    cycles = [
        summarize_cycle(index, component, nodes, cycle_edges)
        for index, component in enumerate(ranked_cycles[:MAX_CYCLES], start=1)
    ]
    return DependencySummary(
        node_count=len(nodes),
        edge_count=len(edges),
        formula_node_count=sum(node.kind == "formula" for node in nodes.values()),
        cross_sheet_edge_count=sum(edge.cross_sheet for edge in edges),
        named_reference_count=sum(node.kind == "named" for node in nodes.values()),
        external_reference_count=sum(node.kind == "external" for node in nodes.values()),
        cluster_count=len(components),
        clusters=clusters,
        cycle_count=len(cycle_components),
        cyclic_node_count=sum(len(component) for component in cycle_components),
        cycles=cycles,
    )


def _build_graph(
    sheet_formulas: list[tuple[str, list[FormulaAnalysis]]],
) -> tuple[dict[str, DependencyNode], list[DependencyEdge]]:
    nodes: dict[str, DependencyNode] = {}
    edges: list[DependencyEdge] = []
    edge_keys: set[tuple[str, str, str]] = set()
    for sheet_name, formulas in sheet_formulas:
        for formula in formulas:
            formula_id = cell_id(sheet_name, formula.cell)
            nodes[formula_id] = DependencyNode(
                formula_id,
                f"{sheet_name}!{normalize_address(formula.cell)}",
                sheet_name,
                normalize_address(formula.cell),
                "formula",
                formula.formula,
            )
            for reference in formula.references:
                node = reference_node(sheet_name, reference)
                if node.id not in nodes or nodes[node.id].kind != "formula":
                    nodes[node.id] = node
                key = (node.id, formula_id, reference)
                if key in edge_keys:
                    continue
                edge_keys.add(key)
                edges.append(
                    DependencyEdge(
                        node.id,
                        formula_id,
                        reference,
                        node.sheet is not None and node.sheet != sheet_name,
                    )
                )
    return nodes, edges


def _adjacency(
    nodes: dict[str, DependencyNode],
    edges: list[DependencyEdge],
    cycle_edges: list[DependencyEdge],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    directed: dict[str, set[str]] = defaultdict(set)
    undirected: dict[str, set[str]] = defaultdict(set)
    for node_id in nodes:
        directed[node_id]
        undirected[node_id]
    for edge in cycle_edges:
        directed[edge.source].add(edge.target)
    for edge in edges:
        undirected[edge.source].add(edge.target)
        undirected[edge.target].add(edge.source)
    return directed, undirected


def _edges_by_component(
    components: list[set[str]],
    edges: list[DependencyEdge],
) -> dict[int, list[DependencyEdge]]:
    positions = {
        node_id: index for index, component in enumerate(components) for node_id in component
    }
    grouped: dict[int, list[DependencyEdge]] = defaultdict(list)
    for edge in edges:
        grouped[positions[edge.source]].append(edge)
    return grouped


__all__ = ["DependencySummary", "analyze_dependencies"]
