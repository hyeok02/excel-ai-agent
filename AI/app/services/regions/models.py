from dataclasses import dataclass

from app.services.semantic_models import SemanticClassification, SemanticReason


@dataclass(frozen=True)
class CellRegion:
    start_cell: str
    end_cell: str
    cell_count: int
    semantic: SemanticClassification | None = None


@dataclass(frozen=True)
class RegionBounds:
    min_row: int
    max_row: int
    min_column: int
    max_column: int
    boundary_reasons: tuple[SemanticReason, ...] = ()
