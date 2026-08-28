from dataclasses import dataclass

from app.services.provenance import Provenance


@dataclass(frozen=True)
class FormulaRiskImpact:
    affected_formula_count: int
    affected_sheet_count: int
    affected_sheets: list[str]
    max_depth: int
    risk_score: int
    risk_level: str


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
    observed_value: str | int | float | bool | None = None
    provenance: Provenance | None = None
    impact: FormulaRiskImpact | None = None


@dataclass(frozen=True)
class FormulaRiskSummary:
    total_count: int
    error_count: int
    warning_count: int
    broken_reference_count: int
    missing_sheet_count: int
    external_reference_count: int
    dynamic_function_count: int
    pattern_mismatch_count: int
    hardcoded_value_count: int
    high_risk_count: int
    critical_risk_count: int
    findings: list[FormulaRiskFinding]

    @classmethod
    def empty(cls) -> "FormulaRiskSummary":
        return cls(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, [])

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
            pattern_mismatch_count=sum(
                item.kind == "formula_pattern_mismatch" for item in findings
            ),
            hardcoded_value_count=sum(
                item.kind == "hardcoded_value" for item in findings
            ),
            high_risk_count=sum(
                item.impact is not None and item.impact.risk_level == "high"
                for item in findings
            ),
            critical_risk_count=sum(
                item.impact is not None and item.impact.risk_level == "critical"
                for item in findings
            ),
            findings=sorted(
                findings,
                key=lambda item: item.impact.risk_score if item.impact else 0,
                reverse=True,
            ),
        )
