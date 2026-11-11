"""Comparable finite scalars with source-derived display units."""
import math
import re

_CURRENCIES = {"$": "USD", "usd": "USD", "€": "EUR", "eur": "EUR",
               "₩": "KRW", "krw": "KRW", "원": "KRW", "명": "명",
               "persons": "명", "people": "명", "£": "GBP", "gbp": "GBP",
               "¥": "¥", "jpy": "JPY", "₹": "INR", "inr": "INR"}


_SCALES = {"k": "천", "천": "천", "m": "백만", "mm": "백만", "mn": "백만", "백만": "백만",
           "b": "십억", "bn": "십억", "십억": "십억"}


def scalar(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def unit(cell):
    from app.agent.query.excel_number_formats import parse_number_format
    fmt = str(cell.get("number_format") or "General")
    spec = parse_number_format(fmt)
    if spec.percent:
        return "%"
    # "M" after #,##0.0,, is the scale Excel already applied, read the way an unscaled divisor is.
    literals = list(dict.fromkeys(_SCALES.get(part.strip().casefold(), part.strip())
                                  for part in re.findall(r'"([^"]+)"', fmt)
                                  if part.strip() and part.strip() not in {"-", "–", "—", "+"}))
    escaped = "".join(re.findall(r"\\([A-Za-z가-힣])", fmt))
    if escaped:
        literals.append(_SCALES.get(escaped.casefold(), escaped))
    unquoted = re.sub(r"\[\$([^\]-]*)(?:-[^\]]+)?\]", r"\1", re.sub(r'"[^"]*"', " ", fmt))
    currencies = sorted({_CURRENCIES.get(token.casefold(), token.upper())
                         for token in re.findall(r"USD|EUR|KRW|GBP|JPY|INR|[$€₩£¥₹]", unquoted, re.I)})
    parts = [_CURRENCIES.get(part.casefold(), part) for part in literals]
    result = " ".join(dict.fromkeys([*parts, *(item for item in currencies if item not in parts)]))
    scale = {1000: "천", 1000000: "백만", 1000000000: "십억"}.get(spec.divisor)
    if spec.divisor != 1 and not re.search(r"천|백만|십억|thousand|million|billion", result, re.I):
        result = f"{scale or str(spec.divisor) + '배 단위'} {result}".strip()
    return result


def displayed_value(cell):
    from app.agent.query.excel_number_formats import parse_number_format, scaled_value
    return scaled_value(cell["value"], parse_number_format(cell.get("number_format")))


def displayed_text(cell, value):
    """A displayed value written with the cell's own decimals ("123.5" under #,##0.0,,"M")."""
    from app.agent.query.excel_number_formats import number_text, parse_number_format
    from app.services.insights.narratives.narrative_values import number
    spec = parse_number_format(cell.get("number_format"))
    return number(value) if spec.mode == "raw" else number_text(value, spec)


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
