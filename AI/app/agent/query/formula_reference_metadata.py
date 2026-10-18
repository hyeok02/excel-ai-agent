"""Immutable source metadata; names never execute expressions or refresh links."""
from dataclasses import dataclass


@dataclass(frozen=True)
class FormulaName:
    name: str
    target: str
    scope: str | None = None
    hidden: bool = False


@dataclass(frozen=True)
class FormulaTable:
    name: str
    sheet: str
    reference: str
    columns: tuple[str, ...]
    headers: int = 1
    totals: int = 0
    calculated_columns: tuple[int, ...] = ()
    total_columns: tuple[int, ...] = ()


@dataclass(frozen=True)
class ReferenceMetadata:
    names: tuple[FormulaName, ...] = ()
    tables: tuple[FormulaTable, ...] = ()
    allowed_sheets: frozenset[str] = frozenset()
    unavailable: str | None = None
