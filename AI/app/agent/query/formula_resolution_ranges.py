"""Bounded, shape-preserving references for scalar lookup/conditional formulas."""
from dataclasses import dataclass

from openpyxl.utils.cell import range_boundaries

from app.agent.query.formula_reference_binding import bind_reference
from app.agent.query.formula_resolution_models import FormulaUnavailable
from app.agent.query.formula_resolution_references import reference_cells
from app.agent.query.formula_resolution_values import numeric


@dataclass(frozen=True)
class FormulaRange:
    references: tuple[str, ...]
    rows: int
    columns: int
    array: bool = False

    @property
    def shape(self) -> tuple[int, int]:
        return self.rows, self.columns

    def vector(self) -> tuple[str, ...]:
        if self.rows != 1 and self.columns != 1:
            raise FormulaUnavailable("unsupported_expression")
        return self.references


def range_argument(node, sheet, resolver) -> FormulaRange:
    if node.kind != "range":
        raise FormulaUnavailable("unsupported_expression")
    bound = bind_reference(node.value, sheet, resolver)
    refs = reference_cells(bound, sheet, resolver.sheets, resolver.limits.max_range_cells)
    address = bound.rsplit("!", 1)[-1].replace("$", "").upper()
    left, top, right, bottom = range_boundaries(address)
    return FormulaRange(tuple(refs), bottom - top + 1, right - left + 1, ":" in address)


def integer_argument(value) -> int:
    number = numeric(value)
    if number != number.to_integral_value() or abs(number) > 1048576:
        raise FormulaUnavailable("unsupported_expression")
    return int(number)


def optional_integer(args, position, default, evaluate) -> int:
    if position >= len(args) or args[position].kind == "missing":
        return default
    return integer_argument(evaluate(args[position]))
