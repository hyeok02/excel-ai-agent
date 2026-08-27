package com.hyeok02.excelaiagent.integration.ai.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiAnalysisEvidence(
		String kind,
		@JsonProperty("sheet_name") String sheetName,
		String reference,
		String description,
		Object value,
		String formula) {
}
