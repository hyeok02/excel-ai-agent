package com.hyeok02.excelaiagent.integration.ai;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonAlias;

public record AiWorkbookQuestion(
		String question,
		String answer,
		String status,
		double confidence,
		@JsonAlias("selected_tools") List<String> selectedTools,
		List<Evidence> evidence,
		List<String> limitations,
		Verification verification) {

	public AiWorkbookQuestion {
		if (verification == null) {
			verification = new Verification("unverified", List.of());
		}
	}

	public AiWorkbookQuestion(String question, String answer, String status,
			double confidence, List<String> selectedTools, List<Evidence> evidence,
			List<String> limitations) {
		this(question, answer, status, confidence, selectedTools, evidence, limitations, null);
	}

	public record Verification(String level, List<String> checks) {
	}

	public record Evidence(
			String kind,
			@JsonAlias("sheet_name") String sheetName,
			String reference,
			String description,
			Object value,
			String formula,
			String label,
			@JsonAlias("number_format") String numberFormat) {

		public Evidence(String kind, String sheetName, String reference, String description,
				Object value, String formula, String label) {
			this(kind, sheetName, reference, description, value, formula, label, null);
		}
	}
}
