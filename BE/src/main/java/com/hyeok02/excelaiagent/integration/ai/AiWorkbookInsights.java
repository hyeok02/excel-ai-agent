package com.hyeok02.excelaiagent.integration.ai;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonSetter;
import com.fasterxml.jackson.annotation.Nulls;

public record AiWorkbookInsights(
		AiWorkbookSummary workbook,
		InsightReport report) {

	public static AiWorkbookInsights summaryOnly(AiWorkbookSummary workbook) {
		return new AiWorkbookInsights(workbook, null);
	}

	public record InsightReport(
			String overview,
			List<Insight> insights,
			List<String> limitations,
			Validation validation) {
		public InsightReport(String overview, List<Insight> insights, List<String> limitations) {
			this(overview, insights, limitations, null);
		}
	}

	public record Validation(
			@JsonProperty("generated_count") int generatedCount,
			@JsonProperty("verified_count") int verifiedCount,
			@JsonProperty("limited_count") int limitedCount,
			@JsonProperty("blocked_count") int blockedCount,
			List<String> notices,
			@JsonProperty("overview_validated")
			@JsonSetter(nulls = Nulls.AS_EMPTY) boolean overviewValidated) {
		public Validation(
				int generatedCount, int verifiedCount, int limitedCount,
				int blockedCount, List<String> notices) {
			this(generatedCount, verifiedCount, limitedCount, blockedCount, notices, false);
		}
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
			String description,
			@JsonProperty("validation_status") String validationStatus,
			@JsonProperty("validation_reasons") List<String> validationReasons) {
		public Insight(
				String title, String fact, String cause, String impact,
				String category, String severity, List<String> evidence,
				String recommendation, Double confidence) {
			this(title, fact, cause, impact, category, severity,
					evidence, recommendation, confidence, null, null, List.of());
		}

		public Insight(
				String title, String fact, String cause, String impact,
				String category, String severity, List<String> evidence,
				String recommendation, Double confidence, String description) {
			this(title, fact, cause, impact, category, severity,
					evidence, recommendation, confidence, description, null, List.of());
		}
	}
}
