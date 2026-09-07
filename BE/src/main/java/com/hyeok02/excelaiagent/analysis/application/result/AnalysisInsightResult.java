package com.hyeok02.excelaiagent.analysis.application.result;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonSetter;
import com.fasterxml.jackson.annotation.Nulls;

public final class AnalysisInsightResult {
	private AnalysisInsightResult() {
	}

	public record Report(
			String overview, List<Insight> insights, List<String> limitations,
			Validation validation) {
	}

	public record Validation(
			int generatedCount, int verifiedCount, int limitedCount,
			int blockedCount, List<String> notices,
			@JsonSetter(nulls = Nulls.AS_EMPTY) boolean overviewValidated) {
		public Validation(
				int generatedCount, int verifiedCount, int limitedCount,
				int blockedCount, List<String> notices) {
			this(generatedCount, verifiedCount, limitedCount, blockedCount, notices, false);
		}
	}

	public record Insight(
			String title, String fact, String cause, String impact,
			String category, String severity, List<String> evidence,
			String recommendation, Double confidence,
			String validationStatus, List<String> validationReasons) {
	}
}
