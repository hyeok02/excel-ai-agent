"""Unambiguous named calendar months, independent of workbook and locale."""
import re
from datetime import datetime

_MONTH_NAMES = {name.casefold(): month for month, names in enumerate((
    ("Jan", "January"), ("Feb", "February"), ("Mar", "March"), ("Apr", "April"),
    ("May",), ("Jun", "June"), ("Jul", "July"), ("Aug", "August"),
    ("Sep", "Sept", "September"), ("Oct", "October"), ("Nov", "November"), ("Dec", "December"),
), 1) for name in names}


def named_month(value):
    match = re.fullmatch(r"((?:19|20)\d{2})[\s/-]+([A-Za-z]+)\.?|([A-Za-z]+)\.?[\s/-]+((?:19|20)\d{2})", value.strip())
    if match is None:
        return None
    year, name = (match[1], match[2]) if match[1] else (match[4], match[3])
    month = _MONTH_NAMES.get(name.casefold())
    return datetime(int(year), month, 1) if month else None
