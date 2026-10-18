"""Request-local source reads distinguish unavailable data from confirmed blanks."""
from dataclasses import dataclass
from time import monotonic


class SourceReadError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class SourceSheet:
    name: str
    rows: int
    columns: int
    hidden_rows: frozenset[int] = frozenset()
    hidden_columns: frozenset[str] = frozenset()
    merged_ranges: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceReadLimits:
    max_cells: int = 2_000_000
    max_rows: int = 250_000
    max_reads: int = 16
    max_seconds: float = 20.0


class SourceBudget:
    def __init__(self, limits):
        self.limits = limits
        self.cells = self.rows = self.reads = 0
        self.seconds = 0.0

    def begin(self):
        self.reads += 1
        if self.reads > self.limits.max_reads:
            raise SourceReadError("resource_limit")
        return monotonic()

    def check(self, started, width=0):
        if self.seconds + monotonic() - started > self.limits.max_seconds:
            raise SourceReadError("time_limit")
        if width:
            self.cells += width
            self.rows += 1
        if self.cells > self.limits.max_cells or self.rows > self.limits.max_rows:
            raise SourceReadError("resource_limit")

    def finish(self, started):
        self.seconds += monotonic() - started
