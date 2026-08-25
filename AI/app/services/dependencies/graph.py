from collections import defaultdict, deque


def connected_components(adjacency: dict[str, set[str]]) -> list[set[str]]:
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


def strongly_connected_components(
    adjacency: dict[str, set[str]],
) -> list[set[str]]:
    finish_order = _finish_order(adjacency)
    reverse = _reverse_adjacency(adjacency)
    components: list[set[str]] = []
    visited: set[str] = set()
    for start_node in reversed(finish_order):
        if start_node in visited:
            continue
        component: set[str] = set()
        stack = [start_node]
        visited.add(start_node)
        while stack:
            node_id = stack.pop()
            component.add(node_id)
            for neighbor in sorted(reverse[node_id], reverse=True):
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        components.append(component)
    return components


def _finish_order(adjacency: dict[str, set[str]]) -> list[str]:
    order: list[str] = []
    visited: set[str] = set()
    for start_node in sorted(adjacency):
        if start_node in visited:
            continue
        stack: list[tuple[str, bool]] = [(start_node, False)]
        while stack:
            node_id, expanded = stack.pop()
            if expanded:
                order.append(node_id)
                continue
            if node_id in visited:
                continue
            visited.add(node_id)
            stack.append((node_id, True))
            for neighbor in sorted(adjacency[node_id], reverse=True):
                if neighbor not in visited:
                    stack.append((neighbor, False))
    return order


def _reverse_adjacency(adjacency: dict[str, set[str]]) -> dict[str, set[str]]:
    reverse: dict[str, set[str]] = defaultdict(set)
    for node_id in adjacency:
        reverse[node_id]
    for source, targets in adjacency.items():
        for target in targets:
            reverse[target].add(source)
    return reverse
