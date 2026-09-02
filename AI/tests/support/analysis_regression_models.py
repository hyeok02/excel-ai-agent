from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol

KEEP = "keep"
DROP = "drop"
SPECIFIC = "specific"
CLARIFY = "clarify"


@dataclass(frozen=True)
class MetricChange:
    metric: str
    earliest_period: str
    earliest_value: float
    latest_period: str
    latest_value: float
    change: float
    change_rate_percent: float

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> MetricChange:
        return cls(
            metric=str(payload["metric"]),
            earliest_period=str(payload["earliest_period"]),
            earliest_value=float(payload["earliest_value"]),
            latest_period=str(payload["latest_period"]),
            latest_value=float(payload["latest_value"]),
            change=float(payload["change"]),
            change_rate_percent=float(payload["change_rate_percent"]),
        )

    def fields(self) -> dict[str, object]:
        return {
            "earliest_period": self.earliest_period,
            "earliest_value": self.earliest_value,
            "latest_period": self.latest_period,
            "latest_value": self.latest_value,
            "change": self.change,
            "change_rate_percent": self.change_rate_percent,
        }


@dataclass(frozen=True)
class AnalysisPrediction:
    """워크북 하나에 대한 결정론 판정 묶음.

    LLM 문장을 고정하지 않고, 그 문장을 우리 검증기가 어떻게 처리하는지만
    고정한다. 그래야 모델이 바뀌어도 기대값이 흔들리지 않는다.
    """

    workbook: str
    subject: str | None
    changes: tuple[MetricChange, ...]
    review_points: Mapping[str, str]
    questions: Mapping[str, str]


@dataclass(frozen=True)
class AnalysisFixtureCase:
    name: str
    workbook_path: Path
    expected: AnalysisPrediction
    coverage: tuple[str, ...]
    review_point_texts: tuple[str, ...]
    question_texts: tuple[str, ...]


class AnalysisPredictor(Protocol):
    def predict(self, case: AnalysisFixtureCase) -> AnalysisPrediction:
        """픽스처 워크북을 실제 분석 경로로 통과시켜 판정을 만든다."""
