package com.hyeok02.excelaiagent.analysis.application.result;

import java.util.List;

public final class AnalysisSemanticResult {
	private AnalysisSemanticResult() {
	}

	public record Inclusion(String decision, String reasonCode, String reason) {
	}

	public record SheetClassification(
			String role, String importance, double confidence, int importanceScore,
			List<Reason> reasons) {
	}

	public record Semantic(String role, double confidence, List<Reason> reasons) {
	}

	public record Reason(String code, String message, List<String> evidenceCells) {
	}
}
