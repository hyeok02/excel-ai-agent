"""Recognize explicit checklist status tokens, not numeric values or words."""
import re

SYMBOLS = {
    "o": "o", "0": "o", "○": "o", "◯": "o", "●": "o",
    "x": "x", "×": "x", "✕": "x", "✗": "x",
    "△": "△", "▲": "△", "▽": "△",
    "v": "v", "✓": "v", "✔": "v", "√": "v",
    "?": "?", "-": "-", "ー": "-", "–": "-",
}


def mark_of(value):
    # A fraction such as 0.34, a negative number or a word beginning with x/o
    # is not a mark. Notes are permitted only after a separated mark or an
    # opening bracket, as in "△(pending)" and "✓ inspected".
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or (len(text) > 1 and not re.match(r"[\s(（\[]", text[1])):
        return None
    return SYMBOLS.get(text[:1].casefold())
