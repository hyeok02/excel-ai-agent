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
    context: tuple[tuple[str, str], ...] = ()
    # Coordinate-bound header ancestors, unlike nearby descriptive context.
    # The leaf stays unchanged so its value can be read back from the source.
    header_path: tuple[tuple[str, str], ...] = ()
    # Identifiers in a labeled metadata band identify columns, not record rows.
    source_identifiers: tuple[tuple[str, str], ...] = ()

    @property
    def display_header(self):
        return " / ".join(dict.fromkeys([text for _, text in self.header_path] + [self.header]))


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
    context: tuple[tuple[str, str], ...] = ()
    hidden_columns: frozenset[str] = frozenset()
    source_kind: str = "sample"
    metadata_rows: frozenset[int] = frozenset()
