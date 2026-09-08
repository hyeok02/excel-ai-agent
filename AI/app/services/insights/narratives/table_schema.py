"""Generic column roles shared by structured-table narratives."""
import re

from openpyxl.utils.cell import coordinate_from_string, column_index_from_string

ROLE_PATTERNS = (
    ("rank", re.compile(r"\brank(?:ing)?\b|순위|등수", re.I)),
    ("name", re.compile(r"\b(?:owner|holder|investor|company)?\s*name\b|이름|명칭|보유자명|투자자명|주주명", re.I)),
    ("share", re.compile(r"%|percent|percentage|비중|구성비|지분율|보유율", re.I)),
    ("quantity", re.compile(r"quantity|amount|count|shares?\s*(?:held|owned)|수량|주식수|보유\s*수", re.I)),
    ("category", re.compile(r"\b(?:category|type|class|group)\b|유형|구분|분류", re.I)),
)


def detect_schema(rows):
    best = None
    for index, row in enumerate(rows[:6]):
        schema, unused, headers = {}, [], {}
        for cell in row:
            text = str(cell.get("value", "")).strip()
            role = next((name for name, pattern in ROLE_PATTERNS if pattern.search(text)), None)
            position = column(cell)
            if role and role not in schema:
                schema[role], headers[role] = position, text
            elif text:
                unused.append((position, text))
        valid = "share" in schema and (
            {"rank", "name"} <= schema.keys() or unused or "category" in schema
        )
        if not valid:
            continue
        if "category" not in schema and unused:
            schema["label"], headers["label"] = min(unused)
        elif "category" in schema:
            schema["label"], headers["label"] = schema["category"], headers["category"]
        score = len(schema) + (3 if {"rank", "name"} <= schema.keys() else 0)
        if best is None or score > best[0]:
            best = score, index, schema, headers
    return (best[1], best[2], best[3]) if best else None


def column(cell):
    return column_index_from_string(coordinate_from_string(cell["cell"])[0])


def share_value(cell):
    value = float(cell["value"])
    number_format = str(cell.get("number_format", ""))
    return value * 100 if "%" in number_format and abs(value) <= 1 else value
