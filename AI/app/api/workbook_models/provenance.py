from pydantic import BaseModel, ConfigDict

from app.services.provenance import AnalysisMethod, EvidenceKind


class AnalysisEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    kind: EvidenceKind
    sheet_name: str
    reference: str | None
    description: str
    value: str | int | float | bool | None
    formula: str | None


class ProvenanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    analyzer: str
    method: AnalysisMethod
    confidence: float | None
    evidence: list[AnalysisEvidenceResponse]
