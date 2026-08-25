from openpyxl.utils import get_column_letter


def chart_title(chart: object) -> str | None:
    title = getattr(chart, "title", None)
    if isinstance(title, str):
        return title

    rich_text = nested_attr(title, "tx", "rich")
    paragraphs = getattr(rich_text, "p", []) if rich_text is not None else []
    parts: list[str] = []
    for paragraph in paragraphs:
        for run in getattr(paragraph, "r", []) or []:
            text = getattr(run, "t", None)
            if text:
                parts.append(str(text))
        for field in getattr(paragraph, "fld", []) or []:
            text = getattr(field, "t", None)
            if text:
                parts.append(str(text))
    return "".join(parts) or None


def chart_anchor(chart: object) -> str | None:
    marker = getattr(getattr(chart, "anchor", None), "_from", None)
    row = getattr(marker, "row", None)
    column = getattr(marker, "col", None)
    if not isinstance(row, int) or not isinstance(column, int):
        return None
    return f"{get_column_letter(column + 1)}{row + 1}"


def nested_attr(value: object, *attributes: str) -> object | None:
    current = value
    for attribute in attributes:
        if current is None:
            return None
        current = getattr(current, attribute, None)
    return current
