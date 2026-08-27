package com.hyeok02.excelaiagent.analysis.application.result;

import com.hyeok02.excelaiagent.integration.ai.model.AiAnalysisEvidence;
import com.hyeok02.excelaiagent.integration.ai.model.AiProvenance;

final class ProvenanceResultMapper {
	private ProvenanceResultMapper() {
	}

	static AnalysisProvenanceResult.Provenance map(AiProvenance provenance) {
		if (provenance == null) {
			return null;
		}
		return new AnalysisProvenanceResult.Provenance(
				provenance.analyzer(), provenance.method(), provenance.confidence(),
				SemanticResultMapper.safe(provenance.evidence()).stream()
						.map(ProvenanceResultMapper::map).toList());
	}

	private static AnalysisProvenanceResult.Evidence map(AiAnalysisEvidence evidence) {
		return new AnalysisProvenanceResult.Evidence(
				evidence.kind(), evidence.sheetName(), evidence.reference(),
				evidence.description(), evidence.value(), evidence.formula());
	}
}
