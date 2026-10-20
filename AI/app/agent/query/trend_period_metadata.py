"""Preserve explicit actual/estimate suffixes independently of table layout."""
import re

from app.agent.query.metric_observation_periods import source_period_grain


def trend_period_metadata(value):
    if isinstance(value, str) and re.fullmatch(r"(?:FY\s*)?(?:19|20)\d{2}\s*[AE]", value.strip(), re.I):
        return "annual", "actual" if value.strip().casefold().endswith("a") else "estimate"
    return source_period_grain(value), None
