"""Clarify only source-proven competing scopes, never invent missing labels."""
import re

from app.agent.query.ambiguity_candidates import clarification_answer
from app.agent.query.ambiguity_metrics import metric_candidates
from app.agent.query.ambiguity_tables import table_candidates
from app.agent.query.metric_scalar_answers import metric_scalar_answer
from app.agent.query.metric_observation_answers import metric_observation_answer

_BROAD = re.compile(r"어떤\s*시트|시트\s*구성|파일\s*(?:설명|구조|요약)|이\s*파일\s*뭐|"
                    r"\b(?:workbook|file)\s+(?:summary|structure|overview)\b", re.I)
_JOIN = re.compile(r"결합|조인|연결해서|\bjoin\b", re.I)
_COMPARISON = re.compile(r"비교|증감|변화|변동|추이|증가율|감소율|"
                         r"\b(?:compare|comparison|change|growth|difference)\b", re.I)


def ambiguous_source_answer(question, summary, data_index, intent=None):
    if _BROAD.search(question) or _JOIN.search(question):
        return None
    if intent is not None and (getattr(intent, "whole_workbook", False)
                               or getattr(intent, "relational_query", None) is not None
                               or getattr(intent, "kind", "other") in {"structure", "formula_risk"}):
        return None
    candidates = metric_candidates(question, data_index)
    if not candidates:
        observed = metric_observation_answer(question, summary, data_index, intent)
        if observed is not None and observed.verification.level == "request_checked":
            return None
        # Source-addressed report slices can resemble header tables. They must
        # not override a uniquely bound scalar whose entire request, value and
        # unit were already independently checked. Genuine snapshot conflicts
        # have been handled above before this narrowly validated bypass.
        scalar = metric_scalar_answer(question, summary, data_index, intent)
        if scalar is not None and scalar.verification.level == "request_checked":
            return None
        # Cross-period/grouped comparisons are not single-table scalar choices.
        # Their period/entity ambiguity was checked above; the comparison
        # executor must validate its own population and source operands.
        if getattr(intent, "kind", "other") == "comparison" or _COMPARISON.search(question):
            return None
        candidates = table_candidates(question, summary, data_index)
    return clarification_answer(question, candidates, summary, data_index) if candidates else None
