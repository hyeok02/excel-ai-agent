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
		Verification verification,
		@JsonAlias("resolved_question") String resolvedQuestion,
		@JsonAlias("clarification_options") List<ClarificationOption> clarificationOptions) {

	public AiWorkbookQuestion {
		if (verification == null) {
			verification = new Verification("unverified", List.of());
		}
		if (clarificationOptions == null) clarificationOptions = List.of();
	}

	public AiWorkbookQuestion(String question, String answer, String status,
			double confidence, List<String> selectedTools, List<Evidence> evidence,
			List<String> limitations, Verification verification, String resolvedQuestion) {
		this(question, answer, status, confidence, selectedTools, evidence, limitations,
				verification, resolvedQuestion, List.of());
	}

	public AiWorkbookQuestion(String question, String answer, String status,
			double confidence, List<String> selectedTools, List<Evidence> evidence,
			List<String> limitations, Verification verification) {
		this(question, answer, status, confidence, selectedTools, evidence, limitations, verification, null);
	}

	public AiWorkbookQuestion(String question, String answer, String status,
			double confidence, List<String> selectedTools, List<Evidence> evidence,
			List<String> limitations) {
		this(question, answer, status, confidence, selectedTools, evidence, limitations, null);
	}

	public record Verification(String level, List<String> checks) {
	}

	public record ClarificationOption(String id, String label, String scope, String details, String question) {
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
