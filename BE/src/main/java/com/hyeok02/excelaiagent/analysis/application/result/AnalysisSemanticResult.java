package com.hyeok02.excelaiagent.analysis.application.result;

import java.util.List;

public final class AnalysisSemanticResult {
	private AnalysisSemanticResult() {
	}

	public record Inclusion(
			String decision, String reasonCode, String reason,
			AnalysisProvenanceResult.Provenance provenance) {
	}

	public record SheetClassification(
			String role, String importance, double confidence, int importanceScore,
			List<Reason> reasons, AnalysisProvenanceResult.Provenance provenance) {
	}

	public record Semantic(
			String role, double confidence, List<Reason> reasons,
			AnalysisProvenanceResult.Provenance provenance) {
	}

	public record Reason(String code, String message, List<String> evidenceCells) {
	}
}
