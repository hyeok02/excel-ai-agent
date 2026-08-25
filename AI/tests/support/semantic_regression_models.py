from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol

from app.services.semantic_models import SemanticRole


@dataclass(frozen=True, order=True)
class UnitPrediction:
    cell_range: str
    unit: str
    source: str


@dataclass(frozen=True)
class RegionPrediction:
    cell_range: str
    role: SemanticRole
    decision: str
    units: tuple[UnitPrediction, ...] = ()


@dataclass(frozen=True)
class SheetPrediction:
    name: str
    decision: str
    sheet_role: str
    regions: tuple[RegionPrediction, ...]


@dataclass(frozen=True)
class SemanticPrediction:
    workbook: str
    sheets: tuple[SheetPrediction, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> SemanticPrediction:
        try:
            sheets = tuple(_sheet_from_mapping(sheet) for sheet in payload["sheets"])
            return cls(workbook=str(payload["workbook"]), sheets=sheets)
        except (KeyError, TypeError) as exception:
            raise ValueError("의미 분석 결과 JSON 형식이 올바르지 않습니다.") from exception


@dataclass(frozen=True)
class SemanticFixtureCase:
    workbook_path: Path
    expectation_path: Path
    coverage: tuple[str, ...]
    expected: SemanticPrediction

    @property
    def name(self) -> str:
        return self.workbook_path.name


class SemanticPredictor(Protocol):
    def predict(self, workbook_path: Path) -> SemanticPrediction:
        """Return semantic labels for one workbook."""


def _sheet_from_mapping(sheet: Mapping[str, object]) -> SheetPrediction:
    return SheetPrediction(
        name=str(sheet["name"]),
        decision=str(sheet["decision"]),
        sheet_role=str(sheet["sheet_role"]),
        regions=tuple(_region_from_mapping(region) for region in sheet["regions"]),
    )


def _region_from_mapping(region: Mapping[str, object]) -> RegionPrediction:
    return RegionPrediction(
        cell_range=str(region["range"]),
        role=SemanticRole(str(region["role"])),
        decision=str(region["decision"]),
        units=tuple(
            UnitPrediction(str(unit["range"]), str(unit["unit"]), str(unit["source"]))
            for unit in region.get("units", [])
        ),
    )
