import json
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.agent.execution.models import AgentExecution, AgentStepStatus
from app.services.insights.numeric_validation import numbers
from app.services.insights.reference_values import index_reference_numbers
from app.services.provenance import EvidenceKind

REFERENCE_PATTERN = re.compile(
    r"(?:'([^']+)'|([^\s!,:;=\"'\[\]{}]+))!\$?([A-Z]{1,3})\$?(\d+)"
    r"(?::\$?([A-Z]{1,3})\$?(\d+))?"
)
CELL_RANGE_PATTERN = re.compile(r"^\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?$")


@dataclass
class EvidenceIndex:
    references: set[str] = field(default_factory=set)
    cause_references: set[str] = field(default_factory=set)
    reference_numbers: dict[str, set[Decimal]] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)


def workbook_evidence_index(context: dict[str, object]) -> EvidenceIndex:
    index = EvidenceIndex()
    for sheet in context.get("sheets", []):
        _index_workbook_sheet(index, sheet)
    if int(context.get("omitted_sheet_count", 0)) > 0:
        index.limitations.append("일부 시트는 인사이트 입력 범위에서 제외되었습니다.")
    return index


def agent_evidence_index(execution: AgentExecution) -> EvidenceIndex:
    index = EvidenceIndex()
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        for evidence in step.result.evidence:
            if not evidence.reference:
                continue
            reference = normalize_reference(
                f"{evidence.sheet_name}!{evidence.reference}"
            )
            if reference:
                index.references.add(reference)
                _add_reference_numbers(index, reference, evidence.value)
                if evidence.kind in {EvidenceKind.FORMULA, EvidenceKind.METADATA}:
                    index.cause_references.add(reference)
    if execution.failed_step_count or execution.skipped_step_count:
        index.limitations.append("실패하거나 건너뛴 Agent 단계의 정보는 검증에 포함되지 않았습니다.")
    return index


def _index_workbook_sheet(index: EvidenceIndex, sheet: Any) -> None:
    if not isinstance(sheet, dict):
        return
    sheet_name = str(sheet.get("name", ""))
    index.references.update(
        extract_references(json.dumps(sheet, ensure_ascii=False, default=str))
    )
    index_reference_numbers(
        index, sheet, sheet_name, extract_references, normalize_reference
    )
    for formula in sheet.get("formula_samples", []):
        cell = formula.get("cell") if isinstance(formula, dict) else None
        if cell:
            reference = normalize_reference(f"{sheet_name}!{cell}")
            if reference:
                index.references.add(reference)
                index.cause_references.add(reference)
    for key, value in _walk_items(sheet):
        if key not in {"location", "reference", "table_range", "anchor_cell"}:
            continue
        reference = normalize_reference(str(value))
        if reference is None and CELL_RANGE_PATTERN.match(str(value)):
            reference = normalize_reference(f"{sheet_name}!{value}")
        if reference:
            index.references.add(reference)


def _walk_items(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk_items(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_items(item)


def _add_reference_numbers(index: EvidenceIndex, reference: str, value: Any) -> None:
    if value is None:
        return
    index.reference_numbers.setdefault(reference, set()).update(numbers(str(value)))


def extract_references(value: str) -> set[str]:
    return {
        normalized
        for match in REFERENCE_PATTERN.finditer(value)
        if (normalized := _normalize_match(match))
    }


def normalize_reference(value: str) -> str | None:
    match = REFERENCE_PATTERN.search(value.replace("$", ""))
    return _normalize_match(match) if match else None


def _normalize_match(match: re.Match[str]) -> str:
    sheet = (match.group(1) or match.group(2)).strip().casefold()
    start = f"{match.group(3)}{match.group(4)}"
    end = f":{match.group(5)}{match.group(6)}" if match.group(5) else ""
    return f"{sheet}!{start}{end}".casefold()
