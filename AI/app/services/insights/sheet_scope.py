"""Keep narrative candidates inside the workbook's primary subject scope."""
import re


COMPARISON = re.compile(
    r"(?<![A-Za-z])(?:peers?|peergroup|comparison|comparable|benchmark|competitors?)"
    r"(?![A-Za-z])"
    r"|비교|벤치마크",
    re.I,
)
INTERNAL = re.compile(r"^_?(?:intermediate|helper|cache|lookup)(?:[_\s-].*)?$", re.I)


def narrative_sheet_groups(context):
    sheets = [
        (index, sheet)
        for index, sheet in enumerate(context.get("sheets", []))
        if isinstance(sheet, dict)
    ]
    visible = [item for item in sheets if not internal_sheet(item[1])]
    sheets = visible or sheets
    primary = [item for item in sheets if not comparison_sheet(item[1])]
    comparisons = [item for item in sheets if comparison_sheet(item[1])]
    return primary, comparisons


def comparison_sheet(sheet):
    return bool(COMPARISON.search(str(sheet.get("name", ""))))


def internal_sheet(sheet):
    classification = sheet.get("sheet_classification") or {}
    role = classification.get("role") if isinstance(classification, dict) else None
    return role in {"documentation", "system"} or bool(
        INTERNAL.fullmatch(str(sheet.get("name", "")).strip())
    )
