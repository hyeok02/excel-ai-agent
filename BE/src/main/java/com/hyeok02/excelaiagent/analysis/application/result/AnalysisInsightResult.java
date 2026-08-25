package com.hyeok02.excelaiagent.analysis.application.result;

import java.util.List;

public final class AnalysisInsightResult {
	private AnalysisInsightResult() {
	}

	public record Report(String overview, List<Insight> insights, List<String> limitations) {
	}

	public record Insight(
			String title, String description, String category, String severity,
			List<String> evidence, String recommendation) {
	}
}
