from collections.abc import Iterable, Mapping
from typing import Any

from app.agent.contracts import InvalidToolArgumentsError, ToolArguments
from app.services.provenance import AnalysisEvidence, Provenance


def optional_string(arguments: ToolArguments, name: str) -> str | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise InvalidToolArgumentsError(f"{name}은 비어 있지 않은 문자열이어야 합니다.")
    return value.strip()


def bounded_integer(
    arguments: ToolArguments,
    name: str,
    default: int,
    maximum: int,
) -> int:
    value = arguments.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise InvalidToolArgumentsError(
            f"{name}은 1 이상 {maximum} 이하의 정수여야 합니다."
        )
    return value


def collect_evidence(
    provenances: Iterable[Provenance | None],
) -> tuple[AnalysisEvidence, ...]:
    collected: list[AnalysisEvidence] = []
    seen: set[tuple[Any, ...]] = set()
    for provenance in provenances:
        if provenance is None:
            continue
        for evidence in provenance.evidence:
            key = (
                evidence.kind,
                evidence.sheet_name,
                evidence.reference,
                evidence.description,
                evidence.formula,
            )
            if key not in seen:
                seen.add(key)
                collected.append(evidence)
    return tuple(collected)


def arguments_or_empty(arguments: ToolArguments | None) -> Mapping[str, Any]:
    return arguments or {}
