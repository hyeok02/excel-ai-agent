package com.hyeok02.excelaiagent.integration.ai.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiFormulaRiskFinding(
		String kind,
		String severity,
		@JsonProperty("sheet_name") String sheetName,
		String cell,
		String message,
		String formula,
		String reference,
		@JsonProperty("function_name") String functionName,
		@JsonProperty("observed_value") Object observedValue,
		AiProvenance provenance,
		AiFormulaRiskImpact impact) {
}
