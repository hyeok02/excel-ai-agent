"""Locate answer boundaries without cutting quoted workbook labels or numbers."""
import re

CLAUSE_BREAK = re.compile(
    r"[!?;\n]|[.,](?=\s|$)|(?:이고|이며|반면|그리고)|\b(?:and|while)\b", re.I
)
SENTENCE_BREAK = re.compile(r"[.!?](?:\s+|$)")
LIST_OR_TABLE = re.compile(r"^\s*(?:[-+*]\s+|\d+[.)]\s+|\|)")
TABLE_SEPARATOR = re.compile(r"^\s*\|?[\s:|-]+\|\s*$")
PAIRS = {"'": "'", '"': '"', "‘": "’", "“": "”", "`": "`"}


def unquoted_breaks(text: str, pattern):
    """Yield delimiters only outside quotes and bracketed source labels."""
    protected = set()
    quote = None
    brackets = []
    for position, char in enumerate(text):
        if quote:
            protected.add(position)
            if char == quote and (not position or text[position - 1] != "\\"):
                quote = None
        elif char in PAIRS and not (
            char in {"'", "‘"} and position and text[position - 1].isalnum()
        ):
            quote = PAIRS[char]
            protected.add(position)
        elif char in "([{":
            brackets.append({"(": ")", "[": "]", "{": "}"}[char])
            protected.add(position)
        elif brackets:
            protected.add(position)
            if char == brackets[-1]:
                brackets.pop()
    for match in pattern.finditer(text):
        if not any(position in protected for position in range(*match.span())):
            yield match


def validation_clauses(text: str) -> list[str]:
    start, parts = 0, []
    for match in unquoted_breaks(text, CLAUSE_BREAK):
        if part := text[start:match.start()].strip():
            parts.append(part)
        start = match.end()
    if part := text[start:].strip():
        parts.append(part)
    return [part for part in parts if not TABLE_SEPARATOR.fullmatch(part)]


def answer_units(text: str) -> list[str]:
    """Keep complete sentences, list items and table rows exactly as authored."""
    units = []
    for line in text.splitlines(keepends=True):
        if LIST_OR_TABLE.match(line):
            units.append(line)
            continue
        start = 0
        for match in unquoted_breaks(line, SENTENCE_BREAK):
            units.append(line[start:match.end()])
            start = match.end()
        if start < len(line):
            units.append(line[start:])
    return units
