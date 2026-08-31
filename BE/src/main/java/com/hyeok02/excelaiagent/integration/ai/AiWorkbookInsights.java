package com.hyeok02.excelaiagent.integration.ai;

import java.util.List;

public record AiWorkbookInsights(
		AiWorkbookSummary workbook,
		InsightReport report) {

	public static AiWorkbookInsights summaryOnly(AiWorkbookSummary workbook) {
		return new AiWorkbookInsights(workbook, null);
	}

	public record InsightReport(
			String overview,
			List<Insight> insights,
			List<String> limitations) {
	}

	public record Insight(
			String title,
			String fact,
			String cause,
			String impact,
			String category,
			String severity,
			List<String> evidence,
			String recommendation,
			Double confidence,
			String description) {
		public Insight(
				String title, String fact, String cause, String impact,
				String category, String severity, List<String> evidence,
				String recommendation, Double confidence) {
			this(title, fact, cause, impact, category, severity,
					evidence, recommendation, confidence, null);
		}
	}
}
