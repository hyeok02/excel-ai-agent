"""Read the money unit a sheet states, instead of leaving bare numbers.

A workbook writes its unit once: either as a note over the table ("in $
Millions") or as the value under a 'Magnitude' label. The second form must be
read positionally — the same words also sit nearby as a dropdown list of
choices, and picking one of those would report a unit never selected.
"""
import re

from openpyxl.utils.cell import coordinate_from_string

from app.services.insights.narrative_values import reference

AMOUNT_NOTE = re.compile(
    r"\bin\s+\$?\s*(millions|billions|thousands)\b"
    r"|단위\s*[:：(]?\s*(백만|십억|천)",
    re.I,
)
AMOUNT_TEXT = {"millions": "백만 달러", "billions": "십억 달러",
               "thousands": "천 달러", "백만": "백만", "십억": "십억", "천": "천"}
MAGNITUDE_LABEL = re.compile(r"^(?:magnitude|단위|규모)$", re.I)
CURRENCY_LABEL = re.compile(r"^(?:currency|통화)$", re.I)
MAGNITUDE = {"millions": "백만", "billions": "십억", "thousands": "천",
             "백만": "백만", "십억": "십억", "천": "천"}
CURRENCY = {"u.s. dollar": "달러", "us dollar": "달러", "usd": "달러",
            "dollar": "달러", "달러": "달러", "미국 달러": "달러",
            "원": "원", "krw": "원", "대한민국 원": "원",
            "euro": "유로", "eur": "유로", "yen": "엔", "jpy": "엔"}
PER_SHARE = re.compile(r"per\s+share|\beps\b|주당", re.I)


def amount_unit(sheet):
    return _note_unit(sheet) or _selected_unit(sheet) or ("", [])


def _note_unit(sheet):
    for cell in _cells(sheet):
        found = AMOUNT_NOTE.search(str(cell.get("value", "")))
        if found and cell.get("cell") and AMOUNT_TEXT.get(
            (found.group(1) or found.group(2)).casefold()
        ):
            key = (found.group(1) or found.group(2)).casefold()
            return AMOUNT_TEXT[key], [_reference(sheet, cell)]
    return None


def _selected_unit(sheet):
    cells = {str(cell["cell"]): cell for cell in _cells(sheet) if cell.get("cell")}
    magnitude = _value_under(cells, MAGNITUDE_LABEL, MAGNITUDE)
    currency = _value_under(cells, CURRENCY_LABEL, CURRENCY)
    if not magnitude or not currency:
        return None
    return (f"{magnitude[0]} {currency[0]}",
            [_reference(sheet, magnitude[1]), _reference(sheet, currency[1])])


def _value_under(cells, label, readings):
    """The value a sheet selected sits directly under its label, not beside it."""
    for address, cell in cells.items():
        if not label.fullmatch(_text(cell)):
            continue
        column, row = coordinate_from_string(address)
        under = cells.get(f"{column}{row + 1}")
        reading = readings.get(_text(under).casefold()) if under else None
        if reading:
            return reading, under
    return None


def _text(cell) -> str:
    return " ".join(str((cell or {}).get("value", "")).split())


def _cells(sheet):
    for region in sheet.get("business_facts", {}).get("table_regions", []):
        for row in region.get("rows", []):
            yield from row


def _reference(sheet, cell):
    return reference(str(sheet.get("name", "")), cell["cell"])
