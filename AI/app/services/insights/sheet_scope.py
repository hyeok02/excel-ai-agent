"""Keep narrative candidates inside the workbook's primary subject scope."""
import re


COMPARISON = re.compile(
    r"(?<![A-Za-z])(?:peers?|peergroup|comparison|comparable|benchmark|competitors?)"
    r"(?![A-Za-z])"
    r"|비교|벤치마크",
    re.I,
)


def narrative_sheet_groups(context):
    sheets = [
        (index, sheet)
        for index, sheet in enumerate(context.get("sheets", []))
        if isinstance(sheet, dict)
    ]
    primary = [item for item in sheets if not comparison_sheet(item[1])]
    comparisons = [item for item in sheets if comparison_sheet(item[1])]
    return primary, comparisons


def comparison_sheet(sheet):
    return bool(COMPARISON.search(str(sheet.get("name", ""))))
