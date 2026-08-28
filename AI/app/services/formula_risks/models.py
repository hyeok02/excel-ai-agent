from dataclasses import dataclass

from app.services.provenance import Provenance


@dataclass(frozen=True)
class FormulaRiskFinding:
    kind: str
    severity: str
    sheet_name: str
    cell: str
    message: str
    formula: str
    reference: str | None = None
    function_name: str | None = None
    provenance: Provenance | None = None


@dataclass(frozen=True)
class FormulaRiskSummary:
    total_count: int
    error_count: int
    warning_count: int
    broken_reference_count: int
    missing_sheet_count: int
    external_reference_count: int
    dynamic_function_count: int
    findings: list[FormulaRiskFinding]

    @classmethod
    def empty(cls) -> "FormulaRiskSummary":
        return cls(0, 0, 0, 0, 0, 0, 0, [])

    @classmethod
    def from_findings(
        cls, findings: list[FormulaRiskFinding]
    ) -> "FormulaRiskSummary":
        return cls(
            total_count=len(findings),
            error_count=sum(item.severity == "error" for item in findings),
            warning_count=sum(item.severity == "warning" for item in findings),
            broken_reference_count=sum(
                item.kind == "broken_reference" for item in findings
            ),
            missing_sheet_count=sum(item.kind == "missing_sheet" for item in findings),
            external_reference_count=sum(
                item.kind == "external_reference" for item in findings
            ),
            dynamic_function_count=sum(
                item.kind == "dynamic_function" for item in findings
            ),
            findings=findings,
        )
