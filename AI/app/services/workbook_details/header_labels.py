from datetime import date, datetime


def header_label(value: object) -> str | None:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or normalized.startswith("=") or len(normalized) > 120:
        return None
    return normalized
