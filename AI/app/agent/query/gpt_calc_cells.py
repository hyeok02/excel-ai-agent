"""Evaluate GPT-written arithmetic over cited cells: the cells' own values, + - * / only."""
import ast
import operator
import re

from app.agent.query.references import normalize_reference

_REFERENCE = re.compile(r"\[([^\[\]]+![A-Za-z]{1,3}\d+)\]")
_OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _evaluate(node, values):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, values)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate(node.left, values), _evaluate(node.right, values))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _evaluate(node.operand, values)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.Constant) and _number(node.value):
        return node.value
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    raise ValueError("unsupported expression")


def evaluate(expression, cells):
    """(result, [(reference, cell)]) for an expression over [Sheet!A1] references, or None.

    ``cells`` maps normalized references to indexed cells; every reference must be a number cell.
    """
    used, names = [], {}

    def name(match):
        reference = match.group(1).strip()
        sheet, _, address = reference.rpartition("!")
        key = normalize_reference(f"'{sheet.strip(chr(39))}'!{address}")
        cell = cells.get(key) or cells.get(normalize_reference(reference))
        if cell is None or not _number(cell.value):
            raise KeyError(reference)
        variable = f"v{len(names)}"
        names[variable] = cell.value
        used.append((reference, cell))
        return variable

    try:
        text = _REFERENCE.sub(name, expression)
        if not used or re.search(r"[A-Za-z_]\w*\s*\(|\*\*|//|%", text):
            return None  # no cell, or a function call / power the arithmetic does not allow
        result = _evaluate(ast.parse(text, mode="eval"), names)
    except (KeyError, ValueError, SyntaxError, ZeroDivisionError, TypeError):
        return None
    return float(result), used


def written(expression, used):
    """The expression with each reference followed by its value: [2024!B5](783)-[2023!B5](849)."""
    values = {reference: cell.value for reference, cell in used}
    return _REFERENCE.sub(lambda match: f"{match.group(1)}({values.get(match.group(1).strip(), '?'):,})", expression)
