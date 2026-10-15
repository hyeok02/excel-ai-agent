import re

from openpyxl.utils.cell import get_column_letter, range_boundaries

from app.agent.query.formula_resolution_models import FormulaUnavailable
from app.services.external_links import references_other_file

_ADDRESS = re.compile(r"^\$?[A-Z]{1,3}\$?[1-9]\d*(?::\$?[A-Z]{1,3}\$?[1-9]\d*)?$", re.I)


def reference_cells(raw: str, current_sheet: str, sheets: set[str], limit: int) -> list[str]:
    if references_other_file(raw) or "|" in raw:
        raise FormulaUnavailable("external_data", (raw,))
    if "!" in raw:
        token, address = raw.rsplit("!", 1)
        sheet = token[1:-1].replace("''", "'") if token.startswith("'") and token.endswith("'") else token
    else:
        sheet, address = current_sheet, raw
    canonical = next((name for name in sheets if name.casefold() == sheet.casefold()), None)
    if not _ADDRESS.fullmatch(address) or ":" in sheet:
        raise FormulaUnavailable("unsupported_reference", (raw,))
    if canonical is None:
        raise FormulaUnavailable("missing_reference", (raw,))
    try:
        left, top, right, bottom = range_boundaries(address.replace("$", "").upper())
    except ValueError:
        raise FormulaUnavailable("unsupported_reference", (raw,)) from None
    if left > right or top > bottom or right > 16384 or bottom > 1048576:
        raise FormulaUnavailable("unsupported_reference", (raw,))
    if (right - left + 1) * (bottom - top + 1) > limit:
        raise FormulaUnavailable("resource_limit", (raw,))
    return [f"{canonical}!{get_column_letter(column)}{row}"
            for row in range(top, bottom + 1) for column in range(left, right + 1)]
