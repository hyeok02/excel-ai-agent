import re

from openpyxl.utils.cell import coordinate_to_tuple, range_boundaries

from app.services.dependencies.models import DependencyEdge, DependencyNode

CELL_OR_RANGE_PATTERN = re.compile(
    r"^\$?[A-Za-z]{1,3}\$?\d+(?::\$?[A-Za-z]{1,3}\$?\d+)?$"
)


def expand_range_formula_edges(
    nodes: dict[str, DependencyNode],
    edges: list[DependencyEdge],
) -> list[DependencyEdge]:
    expanded_edges = list(edges)
    edge_keys = {(edge.source, edge.target, edge.reference) for edge in edges}
    formula_nodes = [node for node in nodes.values() if node.kind == "formula"]
    for edge in edges:
        range_node = nodes[edge.source]
        if range_node.kind != "range" or not range_node.sheet or not range_node.cell:
            continue
        min_column, min_row, max_column, max_row = range_boundaries(range_node.cell)
        for formula_node in formula_nodes:
            if formula_node.sheet != range_node.sheet or not formula_node.cell:
                continue
            row, column = coordinate_to_tuple(formula_node.cell)
            if not (min_row <= row <= max_row and min_column <= column <= max_column):
                continue
            edge_key = (formula_node.id, edge.target, edge.reference)
            if edge_key in edge_keys:
                continue
            edge_keys.add(edge_key)
            expanded_edges.append(
                DependencyEdge(
                    source=formula_node.id,
                    target=edge.target,
                    reference=edge.reference,
                    cross_sheet=formula_node.sheet != nodes[edge.target].sheet,
                )
            )
    return expanded_edges


def reference_node(current_sheet: str, raw_reference: str) -> DependencyNode:
    reference = raw_reference.strip().lstrip("=")
    if "[" in reference:
        return _node(f"external:{reference}", reference, None, None, "external")
    if "!" in reference:
        sheet_token, address = reference.rsplit("!", 1)
        sheet_name = unquote_sheet_name(sheet_token)
        if CELL_OR_RANGE_PATTERN.fullmatch(address):
            return _cell_node(sheet_name, address)
    if CELL_OR_RANGE_PATTERN.fullmatch(reference):
        return _cell_node(current_sheet, reference)
    return _node(f"named:{reference}", reference, None, None, "named")


def cell_id(sheet_name: str, address: str) -> str:
    return f"{sheet_name}!{normalize_address(address)}"


def normalize_address(address: str) -> str:
    return address.replace("$", "").upper()


def unquote_sheet_name(sheet_name: str) -> str:
    if sheet_name.startswith("'") and sheet_name.endswith("'"):
        return sheet_name[1:-1].replace("''", "'")
    return sheet_name


def _cell_node(sheet_name: str, address: str) -> DependencyNode:
    normalized = normalize_address(address)
    return _node(
        cell_id(sheet_name, normalized),
        f"{sheet_name}!{normalized}",
        sheet_name,
        normalized,
        "range" if ":" in normalized else "cell",
    )


def _node(
    node_id: str,
    label: str,
    sheet: str | None,
    cell: str | None,
    kind: str,
) -> DependencyNode:
    return DependencyNode(node_id, label, sheet, cell, kind, None)
