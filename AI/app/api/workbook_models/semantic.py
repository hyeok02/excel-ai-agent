from pydantic import BaseModel, ConfigDict

from app.services.analysis_inclusion import AnalysisDecision
from app.services.semantic_models import SemanticRole
from app.services.sheet_classifier import SheetImportance, SheetRole
from app.api.workbook_models.provenance import ProvenanceResponse


class SemanticReasonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    message: str
    evidence_cells: list[str]


class SemanticClassificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: SemanticRole
    confidence: float
    reasons: list[SemanticReasonResponse]
    provenance: ProvenanceResponse | None = None


class AnalysisInclusionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    decision: AnalysisDecision
    reason_code: str
    reason: str
    provenance: ProvenanceResponse | None = None


class SheetRoleReasonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    message: str
    evidence_cells: list[str]


class SheetClassificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: SheetRole
    importance: SheetImportance
    confidence: float
    importance_score: int
    reasons: list[SheetRoleReasonResponse]
    provenance: ProvenanceResponse | None = None
