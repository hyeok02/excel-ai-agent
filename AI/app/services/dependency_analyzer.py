import re
from collections import defaultdict, deque
from dataclasses import dataclass

from app.services.formula_analyzer import FormulaAnalysis

MAX_CLUSTERS = 8
MAX_NODES_PER_CLUSTER = 18
MAX_EDGES_PER_CLUSTER = 28

CELL_OR_RANGE_PATTERN = re.compile(
    r"^\$?[A-Za-z]{1,3}\$?\d+(?::\$?[A-Za-z]{1,3}\$?\d+)?$"
)


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
class DependencySummary:
    node_count: int
    edge_count: int
    formula_node_count: int
    cross_sheet_edge_count: int
    named_reference_count: int
    external_reference_count: int
    cluster_count: int
    clusters: list[DependencyCluster]

    @classmethod
    def empty(cls) -> "DependencySummary":
        return cls(0, 0, 0, 0, 0, 0, 0, [])


def analyze_dependencies(
    sheet_formulas: list[tuple[str, list[FormulaAnalysis]]],
) -> DependencySummary:
    nodes: dict[str, DependencyNode] = {}
    edges: list[DependencyEdge] = []
    edge_keys: set[tuple[str, str, str]] = set()

    for sheet_name, formulas in sheet_formulas:
        for formula in formulas:
            formula_id = _cell_id(sheet_name, formula.cell)
            nodes[formula_id] = DependencyNode(
                id=formula_id,
                label=f"{sheet_name}!{_normalize_address(formula.cell)}",
                sheet=sheet_name,
                cell=_normalize_address(formula.cell),
                kind="formula",
                formula=formula.formula,
            )

            for reference in formula.references:
                reference_node = _reference_node(sheet_name, reference)
                existing_node = nodes.get(reference_node.id)
                if existing_node is None or existing_node.kind != "formula":
                    nodes[reference_node.id] = reference_node

                edge_key = (reference_node.id, formula_id, reference)
                if edge_key in edge_keys:
                    continue

                edge_keys.add(edge_key)
                edges.append(
                    DependencyEdge(
                        source=reference_node.id,
                        target=formula_id,
                        reference=reference,
                        cross_sheet=(
                            reference_node.sheet is not None
                            and reference_node.sheet != sheet_name
                        ),
                    )
                )

    adjacency: dict[str, set[str]] = defaultdict(set)
    for node_id in nodes:
        adjacency[node_id]
    for edge in edges:
        adjacency[edge.source].add(edge.target)
        adjacency[edge.target].add(edge.source)

    components = _connected_components(adjacency)
    component_by_node = {
        node_id: component_index
        for component_index, component in enumerate(components)
        for node_id in component
    }
    edges_by_component: dict[int, list[DependencyEdge]] = defaultdict(list)
    for edge in edges:
        edges_by_component[component_by_node[edge.source]].append(edge)

    ranked_components = sorted(
        enumerate(components),
        key=lambda item: (
            len(edges_by_component[item[0]]),
            len(item[1]),
        ),
        reverse=True,
    )
    clusters = [
        _summarize_cluster(
            display_index,
            component,
            edges_by_component[component_index],
            nodes,
            adjacency,
        )
        for display_index, (component_index, component) in enumerate(
            ranked_components[:MAX_CLUSTERS],
            start=1,
        )
    ]

    return DependencySummary(
        node_count=len(nodes),
        edge_count=len(edges),
        formula_node_count=sum(node.kind == "formula" for node in nodes.values()),
        cross_sheet_edge_count=sum(edge.cross_sheet for edge in edges),
        named_reference_count=sum(node.kind == "named" for node in nodes.values()),
        external_reference_count=sum(
            node.kind == "external" for node in nodes.values()
        ),
        cluster_count=len(components),
        clusters=clusters,
    )


def _reference_node(current_sheet: str, raw_reference: str) -> DependencyNode:
    reference = raw_reference.strip().lstrip("=")
    if "[" in reference:
        return DependencyNode(
            id=f"external:{reference}",
            label=reference,
            sheet=None,
            cell=None,
            kind="external",
            formula=None,
        )

    if "!" in reference:
        sheet_token, address = reference.rsplit("!", 1)
        sheet_name = _unquote_sheet_name(sheet_token)
        if CELL_OR_RANGE_PATTERN.fullmatch(address):
            normalized_address = _normalize_address(address)
            return DependencyNode(
                id=_cell_id(sheet_name, normalized_address),
                label=f"{sheet_name}!{normalized_address}",
                sheet=sheet_name,
                cell=normalized_address,
                kind="range" if ":" in normalized_address else "cell",
                formula=None,
            )

    if CELL_OR_RANGE_PATTERN.fullmatch(reference):
        normalized_address = _normalize_address(reference)
        return DependencyNode(
            id=_cell_id(current_sheet, normalized_address),
            label=f"{current_sheet}!{normalized_address}",
            sheet=current_sheet,
            cell=normalized_address,
            kind="range" if ":" in normalized_address else "cell",
            formula=None,
        )

    return DependencyNode(
        id=f"named:{reference}",
        label=reference,
        sheet=None,
        cell=None,
        kind="named",
        formula=None,
    )


def _connected_components(adjacency: dict[str, set[str]]) -> list[set[str]]:
    components: list[set[str]] = []
    visited: set[str] = set()

    for start_node in sorted(adjacency):
        if start_node in visited:
            continue

        component: set[str] = set()
        queue = deque([start_node])
        visited.add(start_node)

        while queue:
            node_id = queue.popleft()
            component.add(node_id)
            for neighbor in sorted(adjacency[node_id]):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        components.append(component)

    return components


def _summarize_cluster(
    display_index: int,
    component: set[str],
    component_edges: list[DependencyEdge],
    all_nodes: dict[str, DependencyNode],
    adjacency: dict[str, set[str]],
) -> DependencyCluster:
    sampled_node_ids = _sample_connected_nodes(component, adjacency)
    sampled_node_set = set(sampled_node_ids)
    sampled_edges = [
        edge
        for edge in component_edges
        if edge.source in sampled_node_set and edge.target in sampled_node_set
    ][:MAX_EDGES_PER_CLUSTER]
    sheet_names = sorted(
        {
            all_nodes[node_id].sheet
            for node_id in component
            if all_nodes[node_id].sheet is not None
        }
    )

    return DependencyCluster(
        id=f"cluster-{display_index}",
        node_count=len(component),
        edge_count=len(component_edges),
        formula_count=sum(all_nodes[node_id].kind == "formula" for node_id in component),
        sheet_names=sheet_names,
        nodes=[all_nodes[node_id] for node_id in sampled_node_ids],
        edges=sampled_edges,
        is_truncated=(
            len(component) > len(sampled_node_ids)
            or len(component_edges) > len(sampled_edges)
        ),
    )


def _sample_connected_nodes(
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


def _cell_id(sheet_name: str, address: str) -> str:
    return f"{sheet_name}!{_normalize_address(address)}"


def _normalize_address(address: str) -> str:
    return address.replace("$", "").upper()


def _unquote_sheet_name(sheet_name: str) -> str:
    if sheet_name.startswith("'") and sheet_name.endswith("'"):
        return sheet_name[1:-1].replace("''", "'")
    return sheet_name
