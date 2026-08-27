export type EvidenceKind = 'cell' | 'range' | 'formula' | 'sheet' | 'metadata'
export type AnalysisMethod = 'rule_based' | 'dependency_graph' | 'llm'

export interface AnalysisEvidence {
  kind: EvidenceKind
  sheetName: string
  reference: string | null
  description: string
  value: string | number | boolean | null
  formula: string | null
}

export interface AnalysisProvenance {
  analyzer: string
  method: AnalysisMethod
  confidence: number | null
  evidence: AnalysisEvidence[]
}
