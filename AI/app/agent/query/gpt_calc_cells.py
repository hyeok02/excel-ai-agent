"""Evaluate GPT-written arithmetic over cited cells: the cells' own values, + - * / only."""
import ast
import operator
import re

from openpyxl.utils import get_column_letter, range_boundaries

from app.agent.query.cell_display import _display_cell
from app.agent.query.references import normalize_reference

_REFERENCE = re.compile(r"\[([^\[\]]+![A-Za-z]{1,3}\d+)\]")
_OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _evaluate(node, values):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow) and not any(
            isinstance(part, ast.Name) for part in ast.walk(node.right)):  # (B/A)**(1/3): a growth rate's root
        exponent = _evaluate(node.right, {})
        if abs(exponent) > 10:
            raise ValueError("exponent too large")
        return _evaluate(node.left, values) ** exponent
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate(node.left, values), _evaluate(node.right, values))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _evaluate(node.operand, values)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.Constant) and _number(node.value):
        return node.value
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "abs" and len(node.args) == 1 \
            and not node.keywords:  # "|국어 - 수학|"
        return abs(_evaluate(node.args[0], values))
    raise ValueError("unsupported expression")


def evaluate(expression, cells, labels=frozenset(), ranges=None):
    """(result, [(reference, cell)]) for an expression over [Sheet!A1] references, or None.

    ``cells`` maps normalized references to indexed cells; every reference must be a number cell
    and none a header (``labels``): the header "2022" above a column is its name, not a value.
    ``ranges``: every indexed cell, read only where SUM(…) names a whole range (its rows need not be shown).
    """
    used, names, spanned = [], {}, {}

    def name(match):
        reference = match.group(1).strip()
        sheet, _, address = reference.rpartition("!")
        key = normalize_reference(f"'{sheet.strip(chr(39))}'!{address}")
        cell = cells.get(key) or cells.get(normalize_reference(reference)) or spanned.get(key)
        if cell is None or not _number(cell.value) or key in labels or normalize_reference(reference) in labels:
            raise KeyError(reference)
        variable = f"v{len(names)}"
        names[variable] = cell.value
        used.append((reference, cell))
        return variable

    try:
        text = _REFERENCE.sub(name, _expanded(expression, ranges or cells, labels, spanned)).replace("^", "**")
        if not used or re.search(r"[A-Za-z_]\w*\s*\(|//|%", text):
            return None  # no cell, or a function call / power the arithmetic does not allow
        result = _evaluate(ast.parse(text, mode="eval"), names)
    except (KeyError, ValueError, SyntaxError, ZeroDivisionError, TypeError):
        return None
    return float(result), used


_RANGE_CALL = re.compile(r"\b(SUM|AVERAGE)\s*\(\s*(?:\[([^\[\]]+![A-Za-z]{1,3}\d+:[A-Za-z]{1,3}\d+)\]|((?:'[^']+'|[^\s\[\]()!]+)"
                         r"![A-Za-z]{1,3}\d+:[A-Za-z]{1,3}\d+))\s*\)", re.I)  # [Cost variations!B4:B318] keeps its space
MAX_RANGE = 400


def _expanded(expression, cells, labels, spanned=None):
    """SUM(2023!B4:B15) written out as ([2023!B4]+…+[2023!B15]) over its number cells; AVERAGE divided by their count."""
    def expand(match):
        sheet, _, area = (match.group(2) or match.group(3)).rpartition("!")
        left, top, right, bottom = range_boundaries(area)
        if (right - left + 1) * (bottom - top + 1) > MAX_RANGE:
            raise ValueError("range too large")
        listed = []
        for row in range(top, bottom + 1):
            for column in range(left, right + 1):
                reference = f"{sheet}!{get_column_letter(column)}{row}"
                cell = cells.get(normalize_reference(f"'{sheet.strip(chr(39))}'!{get_column_letter(column)}{row}"))
                if cell is not None and _number(cell.value) and normalize_reference(cell.reference) not in labels:
                    listed.append(f"[{reference}]")
                    if spanned is not None:
                        spanned[normalize_reference(f"'{sheet.strip(chr(39))}'!{get_column_letter(column)}{row}")] = cell
        if not listed:
            raise ValueError("no number in the range")
        total = "+".join(listed)
        return f"({total})" if match.group(1).upper() == "SUM" else f"(({total})/{len(listed)})"
    return _RANGE_CALL.sub(expand, expression)


def written(expression, used):
    """The expression with each reference followed by its value as the source shows it:
    [2024!B5](783)-[2023!B5](849), [Sheet1!AA3](5.0%)."""
    values = {reference: _display_cell(cell.value, cell.number_format) for reference, cell in used}
    return _REFERENCE.sub(lambda match: f"{match.group(1)}({values.get(match.group(1).strip(), '?')})", expression)


def result_style(expression, used):
    """A sum or difference of cells in one format is shown in it (5.0% - 4.7% = 0.3%); else plainly."""
    styles = {cell.number_format for _, cell in used}
    # An average written out, (B2+C2+D2)/3, stays in its cells' format: 19.7%, not 0.2.
    inner = re.fullmatch(r"\s*\((.*)\)\s*/\s*\d+(?:\.\d+)?\s*", expression)
    return next(iter(styles)) if len(styles) == 1 and not re.search(r"[*/]", inner.group(1) if inner else expression) \
        else None
