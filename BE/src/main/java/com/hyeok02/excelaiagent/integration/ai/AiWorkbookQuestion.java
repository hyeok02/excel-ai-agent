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
		List<String> limitations) {

	public record Evidence(
			String kind,
			@JsonAlias("sheet_name") String sheetName,
			String reference,
			String description,
			Object value,
			String formula,
			String label) {
	}
}
