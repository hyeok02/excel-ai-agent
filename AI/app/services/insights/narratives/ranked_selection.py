"""Keep useful interpretations alongside aggregate and individual source facts."""


def select_ranked_candidates(candidates):
    groups = {
        "concentration": [item for item in candidates if item[0] == "concentration"],
        "interpretation": [item for item in candidates if item[0] == "interpretation"],
        "aggregate": [item for item in candidates if item[0] in {"total", "aggregate"}],
        "rank": [item for item in candidates if item[0] == "rank"],
        "component": [item for item in candidates if item[0] == "component"],
    }
    chosen = []
    for group in ("concentration", "interpretation", "aggregate", "rank", "aggregate"):
        options = [item for item in groups[group] if item not in chosen]
        if options:
            chosen.append(max(options, key=_priority))
    remaining = sorted((item for item in candidates if item not in chosen),
                       key=_priority, reverse=True)
    return (chosen + remaining)[:5]


def _priority(candidate):
    return -candidate[3], candidate[1]
