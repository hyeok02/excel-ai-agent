"""Compatibility facade for semantic workbook region detection."""

from app.services.regions import CellRegion, detect_regions

__all__ = ["CellRegion", "detect_regions"]
