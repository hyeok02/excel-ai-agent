"""Conservative Excel equality and bounded wildcard matching; never fuzzy joins."""
from datetime import date
from decimal import Decimal
import re

from app.agent.query.formula_resolution_models import FormulaUnavailable
from app.agent.query.formula_resolution_operations import compare
from app.agent.query.formula_resolution_values import numeric

_NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?%?$")


def criterion_number(value: str):
    if not _NUMBER.fullmatch(value):
        if _NUMBER.fullmatch(value.strip()) or re.fullmatch(r"[+-]?[\d.,]+", value):
            raise FormulaUnavailable("unsupported_expression")
        return None
    return numeric(Decimal(value.rstrip("%"))) / (100 if value.endswith("%") else 1)


def wildcard_match(pattern: str, value: str) -> bool:
    # A small dynamic program avoids regex backtracking on untrusted workbook text.
    if any(len(char.casefold()) != 1 for char in pattern + value):
        raise FormulaUnavailable("unsupported_expression")
    tokens, position = [], 0
    while position < len(pattern):
        char = pattern[position]
        if char == "~" and position + 1 < len(pattern) and pattern[position + 1] in "*?~":
            position += 1
            tokens.append(("literal", pattern[position].casefold()))
        else:
            tokens.append((char if char in "*?" else "literal", char.casefold()))
        position += 1
    value = value.casefold()
    if len(tokens) * len(value) > 100_000:
        raise FormulaUnavailable("resource_limit")
    previous = [True] + [False] * len(value)
    for kind, char in tokens:
        current = [kind == "*" and previous[0]] + [False] * len(value)
        for index, actual in enumerate(value, 1):
            current[index] = (previous[index] or current[index - 1]) if kind == "*" else (
                previous[index - 1] and (kind == "?" or char == actual))
        previous = current
    return previous[-1]


def exact_match(key, value, wildcards=False) -> bool:
    if key is None or isinstance(key, list):
        raise FormulaUnavailable("unsupported_expression")
    if isinstance(key, str):
        if any(len(char.casefold()) != 1 for char in key + (value if isinstance(value, str) else "")):
            raise FormulaUnavailable("unsupported_expression")
        if value is None and not key:
            raise FormulaUnavailable("unsupported_expression")
        return isinstance(value, str) and (wildcard_match(key, value) if wildcards else key.casefold() == value.casefold())
    if isinstance(key, bool):
        return isinstance(value, bool) and key == value
    if isinstance(key, date):
        return isinstance(value, date) and compare("=", key, value)
    number = numeric(key)
    if value is None and not number:
        raise FormulaUnavailable("unsupported_expression")
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool) and number == numeric(value)


def criterion_match(criterion, value) -> bool:
    if isinstance(criterion, (bool, list)) or criterion is None or isinstance(value, bool):
        raise FormulaUnavailable("unsupported_expression")
    operator, target = "=", criterion
    if isinstance(criterion, str):
        if len(criterion) > 255:
            raise FormulaUnavailable("unsupported_expression")
        for prefix in ("<=", ">=", "<>", "<", ">", "="):
            if criterion.startswith(prefix):
                operator, target = prefix, criterion[len(prefix):]
                break
        if target == "" and operator in ("=", "<>"):
            matched = value is None or value == ""
            return matched if operator == "=" else not matched
        number = criterion_number(target)
        if number is None:
            if isinstance(value, date):
                raise FormulaUnavailable("unsupported_expression")  # No assumed Excel date locale.
            if value is None and operator == "<>" and any(char in target for char in "*?~"):
                raise FormulaUnavailable("unsupported_expression")
            if operator not in ("=", "<>"):
                raise FormulaUnavailable("unsupported_expression")
            matched = isinstance(value, str) and wildcard_match(target, value)
            return matched if operator == "=" else not matched
        target = number
    if isinstance(target, date):
        return isinstance(value, date) and compare(operator, value, target)
    target = numeric(target)
    if isinstance(value, date):
        raise FormulaUnavailable("unsupported_expression")
    if value is None or value == "":
        if operator in ("<", ">", "<=", ">=") or not target:
            raise FormulaUnavailable("unsupported_expression")
        return operator == "<>"
    if isinstance(value, str):
        candidate = criterion_number(value)
        if candidate is None:
            return operator == "<>"
        # Numeric-text criteria coercion differs across spreadsheet engines.
        # Never guess equality or order and publish a zero/partial count.
        raise FormulaUnavailable("unsupported_expression")
    return compare(operator, numeric(value), target)
