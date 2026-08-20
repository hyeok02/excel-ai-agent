from openpyxl.worksheet.worksheet import Worksheet


SYSTEM_SHEET_NAMES = {
    "ciohiddencachesheet",
}


def is_business_worksheet(worksheet: Worksheet) -> bool:
    """Return whether a worksheet should be included in user-facing analysis."""
    if worksheet.sheet_state != "visible":
        return False

    normalized_name = worksheet.title.strip().casefold()
    name_without_leading_underscores = normalized_name.lstrip("_")

    if normalized_name in SYSTEM_SHEET_NAMES:
        return False

    return not name_without_leading_underscores.startswith("snloffice")
