"""Currency from a native summary linked to the exact, complete source measure."""
import math
import re

from openpyxl.utils.cell import column_index_from_string, coordinate_from_string, range_boundaries

from app.services.insights.narratives.narrative_values import finite, number

_SYMBOLS = frozenset("$€£¥₩₹")
_CODES = frozenset((
    "USD EUR GBP JPY KRW INR CAD AUD NZD HKD SGD CHF CNY TWD "
    "BRL MXN ZAR SEK NOK DKK PLN CZK HUF TRY RUB AED SAR THB IDR MYR PHP VND"
).split())


def linked_record_currency(context, sheet, header, records, cells):
    """Never borrow a unit by matching a number or a nearby table's caption.

    The parser supplies native pivot source/field links. The insight layer also
    requires the entire source range and its raw sum to match. Only currency is
    inherited: a summary's display scale must not scale the source a second time.
    """
    from app.agent.query.excel_number_formats import parse_number_format

    source_name = str(sheet.get("name", ""))
    positions = [coordinate_from_string(c["cell"]) for c in cells]
    column, first_row = positions[0]
    if positions != [(column, first_row + i) for i in range(len(cells))]:
        return "", []
    header_positions = [coordinate_from_string(c["cell"]) for c in header]
    header_cell = next((c for c in header if coordinate_from_string(c["cell"])[0] == column), None)
    if header_cell is None or any(row != first_row - 1 for _, row in header_positions):
        return "", []
    # The caller computes displayed values. Raw summaries cannot provide the
    # currency for a source that already applies a scale or percentage itself.
    if any((spec := parse_number_format(c.get("number_format"))).divisor != 1
           or spec.multiplier != 1 for c in cells):
        return "", []
    total = math.fsum(c["value"] for c in cells)
    matches = []
    for summary_sheet in context.get("sheets", []):
        for source in summary_sheet.get("pivot_unit_sources", []):
            if (source.get("source_sheet") != source_name
                    or source.get("source_column") != column
                    or source.get("source_header") != header_cell["value"]):
                continue
            try:
                left, top, right, bottom = range_boundaries(source["source_range"])
            except (KeyError, ValueError, TypeError):
                continue
            if top != first_row - 1 or bottom != positions[-1][1] or len(records) != bottom - top:
                continue
            # A clipped region with fewer source columns is not the full table.
            if {column_index_from_string(col) for col, _ in header_positions} != set(range(left, right + 1)):
                continue
            cached = source.get("total_value")
            if not finite(cached) or not math.isclose(total, cached, rel_tol=1e-12, abs_tol=1e-9):
                continue
            currency = _currency(source.get("number_format"))
            if currency and source.get("reference"):
                matches.append((currency, source["reference"]))
    if len({currency for currency, _ in matches}) != 1:
        return "", []  # No declaration, or conflicting source-linked currencies.
    return matches[0][0], list(dict.fromkeys(ref for _, ref in matches))


def _currency(number_format):
    # Read only the positive numeric section. Locale markers are not currency
    # declarations ([$-409]); an explicit symbol/code is required ([$$-409]).
    section = str(number_format or "General").split(";", 1)[0]
    if "%" in section:
        return ""
    section = re.sub(r"\[\$([^\]-]*)(?:-[^\]]+)?\]", r"\1", section)
    codes = {code for code in re.findall(r"(?<![A-Za-z])[A-Z]{3}(?![A-Za-z])", section) if code in _CODES}
    if codes:
        return next(iter(codes)) if len(codes) == 1 else ""
    symbols = set(section) & _SYMBOLS
    return next(iter(symbols)) if len(symbols) == 1 else ""


def record_value(value, unit):
    if unit in _SYMBOLS:
        return f"{unit}{number(value)}"
    return f"{number(value)}{' ' + unit if unit else ''}"
