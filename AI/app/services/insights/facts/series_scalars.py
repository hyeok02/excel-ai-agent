"""Comparable finite scalars with source-derived display units."""
import math
import re

_CURRENCIES = {"$": "USD", "usd": "USD", "€": "EUR", "eur": "EUR",
               "₩": "KRW", "krw": "KRW", "원": "KRW", "명": "명",
               "persons": "명", "people": "명", "£": "GBP", "gbp": "GBP",
               "¥": "¥", "jpy": "JPY", "₹": "INR", "inr": "INR"}


def scalar(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def unit(cell):
    from app.agent.query.excel_number_formats import parse_number_format
    fmt = str(cell.get("number_format") or "General")
    spec = parse_number_format(fmt)
    if spec.percent:
        return "%"
    literals = [part.strip() for part in re.findall(r'"([^"]+)"', fmt) if part.strip()]
    escaped = "".join(re.findall(r"\\([A-Za-z가-힣])", fmt))
    if escaped:
        literals.append(escaped)
    if literals:
        result = " ".join(_CURRENCIES.get(part.casefold(), part) for part in literals)
    else:
        fmt = re.sub(r"\[\$([^\]-]*)(?:-[^\]]+)?\]", r"\1", fmt)
        currencies = set(re.findall(r"USD|EUR|KRW|GBP|JPY|INR|[$€₩£¥₹]", fmt, re.I))
        result = " ".join(sorted({_CURRENCIES.get(token.casefold(), token.upper()) for token in currencies}))
    scale = {1000: "천", 1000000: "백만", 1000000000: "십억"}.get(spec.divisor)
    if spec.divisor != 1 and not re.search(r"천|백만|십억|thousand|million|billion", result, re.I):
        result = f"{scale or str(spec.divisor) + '배 단위'} {result}".strip()
    return result


def displayed_value(cell):
    from app.agent.query.excel_number_formats import parse_number_format, scaled_value
    return scaled_value(cell["value"], parse_number_format(cell.get("number_format")))


def consistent_metric(records, label):
    """Duplicate dates or headers must not silently choose the last matching value."""
    from app.services.insights.facts.fact_trends import date_value
    observed, units = {}, set()
    for record in records:
        matches = [cell for cell in record.get("values", [])[1:] if cell.get("label") == label]
        if len(matches) != 1 or not scalar(matches[0].get("value")):
            return False
        cell = matches[0]
        value = displayed_value(cell)
        date = date_value(str(record["values"][0]["value"]))
        if date in observed and observed[date] != value:
            return False
        observed[date] = value
        units.add(unit(cell))
    return len(observed) >= 2 and len(units) == 1
