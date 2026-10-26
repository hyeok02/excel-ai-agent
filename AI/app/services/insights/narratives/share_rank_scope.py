"""Check ranking identities before missing quantity/share rows are discarded."""
from collections import Counter
import re

from app.services.insights.narratives.narrative_values import finite
from app.services.insights.narratives.table_schema import column


def rank_scope_evidence(rows, schema, selected):
    names = {item["name"].casefold() for item in selected}
    ranks, occurrences, evidence = Counter(), Counter(), []
    for cells in rows:
        row = {column(cell): cell for cell in cells}
        rank_cell, name_cell = row.get(schema["rank"]), row.get(schema["name"])
        rank = rank_cell.get("value") if rank_cell else None
        if isinstance(rank, str) and re.fullmatch(r"\+?\d+(?:\.0+)?", rank.strip()):
            rank = int(rank.strip().split(".", 1)[0])
        name = " ".join(str(name_cell.get("value") or "").split()).casefold() if name_cell else ""
        evidence.extend(cell for cell in (rank_cell, name_cell) if cell)
        if name in names:
            occurrences[name] += 1
        if finite(rank) and int(rank) == rank:
            if 1 <= rank <= len(selected):
                ranks[int(rank)] += 1
        elif any(finite(row.get(schema[role], {}).get("value"))
                 for role in ("quantity", "share")):
            return None  # A populated record has no unambiguous position.
    if (any(ranks[rank] != 1 for rank in range(1, len(selected) + 1))
            or any(occurrences[name] != 1 for name in names)):
        return None
    return evidence
