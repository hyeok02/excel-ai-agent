from app.agent.query.index import IndexedRow
from app.agent.query.search_terms import relevance, search_terms

ANCHOR_LIMIT = 4
CONTENT_MATCH_SCORE = 4
NEIGHBOR_OFFSETS = (0, 1, 2, 3, 4, 8, 7, 6, 5, -1, -2, -3)
SUPPORT_SHEET_MARKERS = ("intermediate", "chart_data", "cache", "lookup", "definition")


def search_rows(
    rows: tuple[IndexedRow, ...], query: str, limit: int
) -> list[IndexedRow]:
    if limit <= 0:
        return []
    terms = search_terms(query)
    anchors = _ranked_anchors(rows, terms)
    if not anchors:
        return sorted(rows, key=lambda row: len(row.cells), reverse=True)[: min(limit, 20)]
    return _round_robin_neighbors(rows, anchors, limit)


def _ranked_anchors(
    rows: tuple[IndexedRow, ...], terms: list[str]
) -> list[IndexedRow]:
    scored = sorted(
        ((relevance(row, terms), position, row) for position, row in enumerate(rows)),
        key=lambda item: (-item[0], item[1]),
    )
    positive = [item for item in scored if item[0] > 0]
    content = [item for item in positive if item[0] >= CONTENT_MATCH_SCORE]
    if content:
        primary = [item for item in content if not _is_support_sheet(item[2])]
        candidates = primary or content
    else:
        candidates = positive
    return _cover_terms(candidates, terms)


def _cover_terms(
    candidates: list[tuple[int, int, IndexedRow]], terms: list[str]
) -> list[IndexedRow]:
    remaining = list(candidates)
    uncovered = set(terms)
    selected: list[IndexedRow] = []
    while remaining and len(selected) < ANCHOR_LIMIT:
        best = max(
            remaining,
            key=lambda item: (
                len(_row_hits(item[2], uncovered)), item[0], -item[1]
            ),
        )
        hits = _row_hits(best[2], uncovered)
        if not hits:
            break
        selected.append(best[2])
        uncovered.difference_update(hits)
        remaining.remove(best)
    if len(selected) < ANCHOR_LIMIT:
        selected.extend(
            row for _, _, row in remaining[: ANCHOR_LIMIT - len(selected)]
        )
    return selected


def _row_hits(row: IndexedRow, terms: set[str]) -> set[str]:
    return {term for term in terms if term in row.search_text}


def _is_support_sheet(row: IndexedRow) -> bool:
    normalized = row.sheet_name.casefold()
    return any(marker in normalized for marker in SUPPORT_SHEET_MARKERS)


def _round_robin_neighbors(
    rows: tuple[IndexedRow, ...], anchors: list[IndexedRow], limit: int
) -> list[IndexedRow]:
    by_location = {(row.sheet_name, row.row_number): row for row in rows}
    selected: set[tuple[str, int]] = set()
    ordered: list[IndexedRow] = []
    for offset in NEIGHBOR_OFFSETS:
        for anchor in anchors:
            key = (anchor.sheet_name, anchor.row_number + offset)
            candidate = by_location.get(key)
            if candidate is None or key in selected:
                continue
            selected.add(key)
            ordered.append(candidate)
            if len(ordered) >= limit:
                return ordered
    return ordered
