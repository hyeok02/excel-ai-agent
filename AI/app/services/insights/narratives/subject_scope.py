"""Choose an explicit subject only when it belongs to the narrated table area."""
from app.services.insights.facts.subject_detection import spanning_subjects
from app.services.insights.narratives.narrative_values import identities
from app.services.insights.verification.reference_matching import (
    overlapping_references,
    related_references,
)
from app.services.insights.verification.validation_index import extract_references


def visible_subject(context, visible) -> str:
    for sheet in context.get("sheets", []):
        if not isinstance(sheet, dict):
            continue
        for holder, references in identities(sheet):
            if holder and any(_related(reference, visible) for reference in references):
                return holder.split(" (")[0].strip()
    for holder, references in spanning_subjects(context):
        if any(
            _related(reference, visible) and not _overlapping(reference, visible)
            for reference in references
        ):
            return holder
    return ""


def _related(value, visible) -> bool:
    return any(
        related_references(source, visible)
        for source in extract_references(value)
    )


def _overlapping(value, visible) -> bool:
    return any(
        overlapping_references(source, visible)
        for source in extract_references(value)
    )
