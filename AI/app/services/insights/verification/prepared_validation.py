"""The source-side half of insight validation, prepared while the model writes its report.

The evidence index and the source-generated insights are read from the workbook alone,
never from the model's report, so they are computed during the model call instead of
after it. Validation itself is unchanged: it reads exactly what it would have built.
"""
from dataclasses import dataclass
from typing import Any

from app.services.analysis_strategy import select_analysis_profile
from app.services.insights.facts.context import build_workbook_context
from app.services.insights.narratives.source_narratives import source_narrative_report
from app.services.insights.verification.validation_index import workbook_evidence_index


@dataclass(frozen=True)
class PreparedValidation:
    context: dict
    index: Any
    canonical: Any


def prepare_validation(summary, depth) -> PreparedValidation:
    context = build_workbook_context(summary, select_analysis_profile(summary, depth))
    # Same order validation uses: the index first, then the source narratives.
    index = workbook_evidence_index(context)
    return PreparedValidation(context, index, source_narrative_report(context))
