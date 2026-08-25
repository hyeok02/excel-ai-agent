package com.hyeok02.excelaiagent.integration.ai.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.hyeok02.excelaiagent.integration.ai.AiAnalysisInclusion;
import com.hyeok02.excelaiagent.integration.ai.AiSheetClassification;

public record AiExcludedSheetSummary(
		String name, String state,
		@JsonProperty("analysis_inclusion") AiAnalysisInclusion analysisInclusion,
		@JsonProperty("sheet_classification") AiSheetClassification sheetClassification) {

	public AiExcludedSheetSummary(String name, String state, AiAnalysisInclusion inclusion) {
		this(name, state, inclusion, null);
	}
}
