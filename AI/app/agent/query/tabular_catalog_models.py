"""Source-addressed tables used by question plans, independent of business labels."""
from dataclasses import dataclass, field

from app.services.workbook_details.models import CellValue


@dataclass(frozen=True)
class QueryColumn:
    id: str
    header: str
    header_reference: str
    sample_values: tuple[CellValue, ...]
    number_formats: tuple[str, ...] = ()


@dataclass(frozen=True)
class QueryRow:
    row_number: int
    values: dict[str, CellValue]
    formulas: dict[str, str] = field(default_factory=dict)
    number_formats: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class QueryTable:
    id: str
    sheet_name: str
    reference: str
    columns: tuple[QueryColumn, ...]
    rows: tuple[QueryRow, ...]
    complete: bool
    excluded_rows: frozenset[int] = frozenset()
