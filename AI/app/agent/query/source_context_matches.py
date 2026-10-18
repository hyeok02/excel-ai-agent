"""Resolve sparse context addresses directly, without scanning a 50k-cell map."""
from app.agent.query.references import MAX_CITATION_AREA, matching_references, normalize_reference
from app.agent.query.source_lookup_references import bind_source_reference
from app.agent.query.workbook_source import source_for
from app.agent.query.workbook_source_models import SourceReadError


def context_matches(reference, cells, index):
    if getattr(index, "source_provider", None) is None:
        normalized = normalize_reference(reference)
        return matching_references(normalized, set(cells)) if normalized else set()
    source = source_for(index)
    if source is None:
        return set()
    try:
        requested = bind_source_reference(reference, source)
    except SourceReadError:
        return set()
    if requested.area > MAX_CITATION_AREA:
        return set()
    return {key for address in requested.addresses()
            if (key := normalize_reference(f"{requested.sheet}!{address}")) in cells}
