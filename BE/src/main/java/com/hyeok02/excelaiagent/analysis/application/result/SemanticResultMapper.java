package com.hyeok02.excelaiagent.analysis.application.result;

import java.util.List;
import com.hyeok02.excelaiagent.integration.ai.AiAnalysisInclusion;
import com.hyeok02.excelaiagent.integration.ai.AiSemanticClassification;
import com.hyeok02.excelaiagent.integration.ai.AiSemanticReason;
import com.hyeok02.excelaiagent.integration.ai.AiSheetClassification;
import com.hyeok02.excelaiagent.integration.ai.AiSheetRoleReason;

final class SemanticResultMapper {
	private SemanticResultMapper() {
	}

	static AnalysisSemanticResult.Inclusion map(AiAnalysisInclusion inclusion) {
		if (inclusion == null) {
			return null;
		}
		return new AnalysisSemanticResult.Inclusion(
				inclusion.decision().value(), inclusion.reasonCode(), inclusion.reason(),
				ProvenanceResultMapper.map(inclusion.provenance()));
	}

	static AnalysisSemanticResult.SheetClassification map(AiSheetClassification classification) {
		if (classification == null) {
			return null;
		}
		return new AnalysisSemanticResult.SheetClassification(
				classification.role().value(), classification.importance().value(),
				classification.confidence(), classification.importanceScore(),
				safe(classification.reasons()).stream().map(SemanticResultMapper::map).toList(),
				ProvenanceResultMapper.map(classification.provenance()));
	}

	static AnalysisSemanticResult.Semantic map(AiSemanticClassification semantic) {
		if (semantic == null) {
			return null;
		}
		return new AnalysisSemanticResult.Semantic(
				semantic.role().value(), semantic.confidence(),
				safe(semantic.reasons()).stream().map(SemanticResultMapper::map).toList(),
				ProvenanceResultMapper.map(semantic.provenance()));
	}

	private static AnalysisSemanticResult.Reason map(AiSheetRoleReason reason) {
		return new AnalysisSemanticResult.Reason(
				reason.code(), reason.message(), safe(reason.evidenceCells()));
	}

	private static AnalysisSemanticResult.Reason map(AiSemanticReason reason) {
		return new AnalysisSemanticResult.Reason(
				reason.code(), reason.message(), safe(reason.evidenceCells()));
	}

	static <T> List<T> safe(List<T> values) {
		return values == null ? List.of() : values;
	}
}
