"""Bounded recovery of uncached formulas from workbook-contained inputs only."""
from datetime import date, datetime
from decimal import DecimalException
from time import monotonic

from openpyxl.styles.numbers import is_date_format

from app.agent.query.formula_resolution_evaluator import evaluate_formula
from app.agent.query.formula_resolution_models import (
    FormulaBudget, FormulaLimits, FormulaResolution, FormulaUnavailable, failure_message,
)
from app.agent.query.formula_resolution_parser import FormulaParser
from app.agent.query.formula_resolution_values import primitive, source_value


class FormulaResolver:
    def __init__(self, index, limits: FormulaLimits | None = None):
        self.index = index
        self.limits = limits or FormulaLimits()
        self.budget = FormulaBudget(self.limits, monotonic())
        self.cells = {cell.reference: cell for row in index.rows for cell in row.cells}
        self.sheets = {row.sheet_name for row in index.rows}
        self.active: set[str] = set()
        self.reference_stack: list[str] = []
        self.memo: dict[str, tuple[object, frozenset[str]]] = {}

    def resolve(self, reference: str) -> FormulaResolution:
        cell = self.cells.get(reference)
        inputs: set[str] = set()
        try:
            value = self.read(reference, inputs)
            if isinstance(value, (date, datetime)) and cell is not None and not is_date_format(cell.number_format):
                raise FormulaUnavailable("unsupported_expression", (reference,))
            value = primitive(value)
            return FormulaResolution(reference, cell.formula if cell else None,
                                     "recovered" if cell and cell.formula and cell.value is None else "cached",
                                     value, tuple(sorted(inputs - {reference})))
        except FormulaUnavailable as error:
            return FormulaResolution(reference, cell.formula if cell else None, "unavailable",
                                     inputs=tuple(sorted(inputs - {reference})), reason=error.reason,
                                     missing_references=error.references,
                                     message=failure_message(error.reason, error.references))
        except (DecimalException, ValueError, OverflowError, RecursionError):
            reason = "calculation_error"
            return FormulaResolution(reference, cell.formula if cell else None, "unavailable",
                                     reason=reason, message=failure_message(reason, ()))

    def resolve_all(self) -> tuple[FormulaResolution, ...]:
        pending = [cell for cell in self.cells.values() if cell.formula and cell.value is None]
        results = [self.resolve(cell.reference) for cell in pending[:self.limits.max_formulas]]
        for cell in pending[self.limits.max_formulas:]:
            results.append(FormulaResolution(cell.reference, cell.formula, "unavailable",
                                            reason="resource_limit", message=failure_message("resource_limit", ())))
        return tuple(results)

    def read(self, reference: str, inputs: set[str], depth: int = 0) -> object:
        self.budget.check(depth, cells=1)
        inputs.add(reference)
        sheet = reference.rsplit("!", 1)[0]
        if sheet not in self.sheets:
            raise FormulaUnavailable("missing_reference", (reference,))
        if self.index.truncated_for({sheet}):
            raise FormulaUnavailable("index_truncated", (reference,))
        cell = self.cells.get(reference)
        if cell is None:
            return None  # Non-truncated indexed sheets omit original blank cells.
        if cell.value is not None or not cell.formula:
            return self.bounded_value(source_value(cell))
        if reference in self.active:
            raise FormulaUnavailable("cycle", (reference,))
        if reference in self.memo:
            value, dependencies = self.memo[reference]
            inputs.update(dependencies)
            return value
        self.active.add(reference)
        self.reference_stack.append(reference)
        dependencies: set[str] = set()
        try:
            parsed = FormulaParser(cell.formula, self.limits).parse()
            value = evaluate_formula(parsed, sheet, self, dependencies, depth + 1)
            if isinstance(value, list):
                raise FormulaUnavailable("unsupported_expression", (reference,))
            value = 0 if value is None else value  # Excel =blank_cell yields zero.
            self.bounded_value(value)
            self.memo[reference] = value, frozenset(dependencies)
            return value
        finally:
            inputs.update(dependencies)
            self.active.remove(reference)
            self.reference_stack.pop()

    def bounded_value(self, value: object) -> object:
        if isinstance(value, str) and len(value) > self.limits.max_result_characters:
            raise FormulaUnavailable("resource_limit")
        return value
