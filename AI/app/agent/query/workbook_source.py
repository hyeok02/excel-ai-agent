"""A bounded, immutable source handle for one uploaded workbook and request."""
from dataclasses import dataclass, field
from hmac import compare_digest

from app.agent.query.workbook_source_models import (
    SourceBudget, SourceReadError, SourceReadLimits, SourceSheet,
)
from app.agent.query.workbook_source_scan import SourceScan


@dataclass(frozen=True)
class WorkbookSource:
    source_digest: str
    sheets: tuple[SourceSheet, ...]
    content: bytes = field(repr=False, compare=False)
    limits: SourceReadLimits = field(default_factory=SourceReadLimits)
    _budget: SourceBudget = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "_budget", SourceBudget(self.limits))

    @property
    def authorized_sheets(self):
        return frozenset(sheet.name for sheet in self.sheets)

    def sheet(self, name):
        matches = [sheet for sheet in self.sheets if sheet.name == name]
        if len(matches) != 1:
            raise SourceReadError("excluded_sheet")
        return matches[0]

    def scan_rows(self, sheet_name, reference):
        return SourceScan(self, self.sheet(sheet_name), reference)


def source_for(index):
    source = getattr(index, "source_provider", None)
    if not isinstance(source, WorkbookSource) or not index.source_digest:
        return None
    return source if compare_digest(source.source_digest, index.source_digest) else None
