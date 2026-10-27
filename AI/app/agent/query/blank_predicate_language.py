"""Shared presence wording; a recorded zero is not a missing value."""
import re

PRESENT_VALUE = re.compile(
    r"(?:값|데이터)(?:이|가)?\s*(?:기록된|입력된|기재된|존재하는|있는)|"
    r"\b(?:non[- ]?(?:blank|empty)|populated|has\s+(?:a\s+)?value)\b", re.I,
)
