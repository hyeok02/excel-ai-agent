"""One semantic gate for cards, auxiliary prose and the generated overview."""
from app.services.insights.verification.claim_grounding import grounded_claim
from app.services.insights.verification.derived_claim_grounding import grounded_derivation
from app.services.insights.verification.numeric_validation import unmatched_numbers
from app.services.insights.verification.relation_grounding import grounded_relations, grounded_metric_owner
from app.services.insights.verification.review_points import grounded_tokens, mask_known_names
from app.services.insights.verification.unit_grounding import grounded_units
from app.services.insights.verification.validation_index import REFERENCE_PATTERN


def grounded_statement(text, index, resolved):
    sources = [text for ref in resolved for text in index.reference_text.get(ref, [])]
    cited = set().union(*(index.reference_numbers.get(ref, set()) for ref in resolved))
    claim = mask_known_names(REFERENCE_PATTERN.sub(" ", text), grounded_tokens(sources))
    return (
        not unmatched_numbers(claim, cited)
        and grounded_claim(text, sources, resolved)
        and grounded_derivation(text, sources, resolved, index.numeric_changes,
                                {label for item in index.observations for label in item.labels})
        and grounded_units(text, sources, resolved, index.numeric_changes)
        and grounded_relations(REFERENCE_PATTERN.sub(" ", text), resolved, index.observations)
        and grounded_metric_owner(REFERENCE_PATTERN.sub(" ", text), resolved, index.observations)
    )
