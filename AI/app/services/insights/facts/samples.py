import re

MAX_FORMULAS_PER_SHEET = 8
MAX_REGIONS_PER_SHEET = 6
MAX_FORMULA_LENGTH = 240
MAX_REFERENCES_PER_FORMULA = 8
MAX_HEADERS_PER_REGION = 6


def truncate_formula(formula: str) -> str:
    return formula if len(formula) <= MAX_FORMULA_LENGTH else f"{formula[:240]}..."


def select_formula_samples(
    formulas: list[dict[str, object]],
    limit: int = MAX_FORMULAS_PER_SHEET,
) -> list[dict[str, object]]:
    samples = []
    seen_signatures: set[str] = set()
    for formula in formulas:
        signature = _formula_signature(formula)
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        samples.append(formula)
        if len(samples) == limit:
            break
    return samples


def select_region_samples(
    regions: list[dict[str, object]],
    limit: int = MAX_REGIONS_PER_SHEET,
) -> list[dict[str, object]]:
    prioritized = sorted(
        enumerate(regions),
        key=lambda item: (-int(item[1].get("cell_count", 0)), item[0]),
    )
    return [_region_sample(region) for _, region in prioritized[:limit]]


def _formula_signature(formula: dict[str, object]) -> str:
    normalized = str(formula["formula"]).upper()
    references = formula.get("references", [])
    if isinstance(references, list):
        for reference in sorted(map(str, references), key=len, reverse=True):
            normalized = normalized.replace(reference.upper(), "<REF>")
    return re.sub(r"\d+", "#", normalized)


def _region_sample(region: dict[str, object]) -> dict[str, object]:
    headers = region.get("header_paths", [])
    return {
        "start_cell": region["start_cell"],
        "end_cell": region["end_cell"],
        "cell_count": region["cell_count"],
        "title": region.get("title"),
        "row_count": region.get("row_count"),
        "column_count": region.get("column_count"),
        "analysis_inclusion": region.get("analysis_inclusion"),
        "merged_range_count": len(region.get("merged_ranges", [])),
        "header_paths": [
            {"column": header.get("column"), "labels": header.get("labels", [])}
            for header in headers[:MAX_HEADERS_PER_REGION]
        ],
    }
