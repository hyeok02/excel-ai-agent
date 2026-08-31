package com.hyeok02.excelaiagent.analysis.application.result;

import java.util.List;

public final class AnalysisInsightResult {
	private AnalysisInsightResult() {
	}

	public record Report(
			String overview, List<Insight> insights, List<String> limitations,
			Validation validation) {
	}

	public record Validation(
			int generatedCount, int verifiedCount, int limitedCount,
			int blockedCount, List<String> notices) {
	}

	public record Insight(
			String title, String fact, String cause, String impact,
			String category, String severity, List<String> evidence,
			String recommendation, Double confidence,
			String validationStatus, List<String> validationReasons) {
	}
}
