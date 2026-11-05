"""Values on a change card as Excel shows them with the source cell's number format.

A percent cell stores 0.0329 and shows 3.3%; the card used to show the stored
number. Every number on the card is shown here with its own cell's format. When
that display hides digits of the new value (2.057 shown as $2.06), the stored
value is given too, and when old and new would read the same, both are given.
"""
import re
from decimal import Decimal, InvalidOperation

from app.agent.query.excel_number_formats import display_value, parse_number_format


def with_displays(change, cell, lookup):
    fmt = cell.number_format
    old, new = shown(change.old_value, fmt), shown(change.new_value, fmt)
    update = {"old_display": old, "new_display": new,
              "new_stored": stored(change.new_value, fmt) if _hides(change.new_value, new) else None}
    if old is not None and old == new and change.old_value != change.new_value:
        update.update(old_stored=stored(change.old_value, fmt), new_stored=stored(change.new_value, fmt))
    update["context_cells"] = [item.model_copy(update={"display": shown(item.value, _format(
        lookup, cell.sheet_name, item.reference))}) for item in change.context_cells]
    update["related_cells"] = [item.model_copy(update={
        "current_display": shown(item.current_value, fmt := _format(lookup, item.sheet_name, item.reference)),
        "suggested_display": shown(item.suggested_value, fmt)}) for item in change.related_cells]
    return change.model_copy(update=update)


def shown(value, number_format):
    """The text Excel shows for a number in this format; None for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if (number_format or "General").strip().casefold() == "general":
        # General shows about ten significant digits, so 1.8699999999999999 reads 1.87.
        text = format(value, ".10g")
        return f"{value:.0f}" if "e" in text and abs(value) >= 1 else text
    try:
        return display_value(value, parse_number_format(number_format))
    except (ValueError, TypeError, InvalidOperation):
        return None


def exact(value, number_format):
    """The shown text only when it keeps every digit of the value; else None."""
    text = shown(value, number_format)
    return None if _hides(value, text) else text


def stored(value, number_format):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if "%" in (number_format or ""):
        return f"{format(value * 100, '.12g')}%"
    return format(value, ".15g")


def _hides(value, text):
    if text is None:
        return False
    digits = re.sub(r"[^0-9.\-]", "", text)
    try:
        number = Decimal(digits) / (100 if "%" in text else 1)
    except InvalidOperation:
        return True
    actual = Decimal(repr(float(value)))
    return abs(number - actual) > Decimal("1e-9") * max(Decimal(1), abs(actual))


def _format(lookup, sheet_name, reference):
    found = lookup.cell(sheet_name, reference)
    return found.number_format if found is not None else None
