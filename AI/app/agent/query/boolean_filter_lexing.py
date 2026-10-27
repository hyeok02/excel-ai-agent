"""Read predicate atoms using exact source headers and quoted/source literals."""
import re

from app.agent.query.tabular_query_models import TabularFilter

CONNECTOR = re.compile(r"\s*(AND\b|OR\b|그리고|및|또는|혹은|이거나|거나|이고|이며|이면서|면서|&&|\|\|)\s*", re.I)
NEGATION = re.compile(r"\s*(?:NOT\b|아닌\s*조건|제외\s*조건)\s*", re.I)
PARTICLE = re.compile(r"\s*(?:이|가|은|는|의)?\s*")
PREFIX = re.compile(r"\s*(is\s+not\b|not\s+equal\s+to\b|!=|≠|>=|<=|≥|≤|>|<|=|is\b|equals?\b|contains?\b|포함)\s*", re.I)
NUMBER = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?(?:\s*(%|퍼센트|percent\b))?", re.I)
SUFFIX = re.compile(r"\s*(?:[이가]\s*)?(아닌|제외|외의|이상|이하|초과|미만|포함된|포함한|포함)(?![가-힣])")
OPS = {"!=": "not_equals", "≠": "not_equals", ">=": "greater_than_or_equal", "≥": "greater_than_or_equal",
       "<=": "less_than_or_equal", "≤": "less_than_or_equal", ">": "greater_than", "<": "less_than",
       "이상": "greater_than_or_equal", "이하": "less_than_or_equal", "초과": "greater_than", "미만": "less_than",
       "아닌": "not_equals", "제외": "not_equals", "외의": "not_equals"}


def leaf_at(text, position, table, inherited=None):
    start = position = spaces(text, position)
    candidates = []
    for column in table.columns:
        for label in (column.header, f"'{column.header}'", f'"{column.header}"'):
            if text[position:position + len(label)].casefold() == label.casefold():
                end = position + len(label)
                if end == len(text) or not re.match(r"[A-Za-z0-9_]", text[end]):
                    candidates.append((len(label), column, end))
    if candidates:
        longest = max(size for size, _, _ in candidates)
        found = [(column, end) for size, column, end in candidates if size == longest]
        if len({column.id for column, _ in found}) != 1:
            return None
        column, position = found[0]
        position = PARTICLE.match(text, position).end()
    elif inherited is not None:
        column = inherited
    else:
        return None
    prefix = PREFIX.match(text, position)
    operator = "equals"
    if prefix:
        operator = operation(prefix[1])
        position = prefix.end()
    value_result = value_at(text, position, table, column)
    if value_result is None:
        return None
    value, unit, end, quoted = value_result
    suffix = SUFFIX.match(text, end)
    if suffix:
        secondary = operation(suffix[1])
        if operator != "equals" and secondary != operator:
            return None
        operator, end = secondary, suffix.end()
        if not candidates and operator == "not_equals":
            return None  # "A or B 제외" does not establish the scope of exclusion.
    if not quoted and isinstance(value, str) and value.casefold() in {"blank", "empty", "null", "빈칸", "공백", "누락"}:
        if operator not in {"equals", "not_equals"}:
            return None
        operator, value = ("is_blank" if operator == "equals" else "not_blank"), None
    tail = re.match(r"\s*인(?=\s|$|[)])", text[end:])
    if tail:
        end += tail.end()
    return TabularFilter(column_id=column.id, operator=operator, value=value, value_unit=unit), end, column, start


def value_at(text, position, table, column):
    position = spaces(text, position)
    if position == len(text):
        return None
    pairs = {"'": "'", '"': '"', "‘": "’", "“": "”"}
    if text[position] in pairs:
        end = text.find(pairs[text[position]], position + 1)
        if end < 0 or end - position > 302:
            return None
        return text[position + 1:end], "raw", end + 1, True
    number = NUMBER.match(text, position)
    if number and boundary(text, number.end()):
        raw = re.match(r"[-+]?\d[\d,]*(?:\.\d+)?", number[0])[0].replace(",", "")
        return (float(raw) if "." in raw else int(raw)), "percent" if number[1] else "raw", number.end(), False
    values = {str(row.values[column.id]) for row in table.rows
              if isinstance(row.values[column.id], str) and row.values[column.id]}
    values |= {"blank", "empty", "null", "빈칸", "공백", "누락", "true", "false"}
    for value in sorted(values, key=len, reverse=True):
        end = position + len(value)
        if (len(value) > 300 or CONNECTOR.search(value) or "(" in value or ")" in value
                or text[position:end].casefold() != value.casefold() or not boundary(text, end)):
            continue
        literal = value.casefold() == "true" if value.casefold() in {"true", "false"} else text[position:end]
        return literal, "raw", end, False
    return None


def boundary(text, end):
    return end == len(text) or bool(re.match(r"[\s),?!]|인|이고|이며|이거나|거나|이면서|[이가]\s*(?:아닌|이상|이하|초과|미만)|아닌|제외|이상|이하|초과|미만", text[end:]))


def operation(token):
    if re.search(r"contains?|포함", token, re.I):
        return "contains"
    if re.search(r"not", token, re.I):
        return "not_equals"
    return OPS.get(token, "equals")


def spaces(text, position):
    return position + len(text[position:]) - len(text[position:].lstrip())
