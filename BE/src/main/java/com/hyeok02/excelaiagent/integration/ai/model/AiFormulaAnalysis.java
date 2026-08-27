package com.hyeok02.excelaiagent.integration.ai.model;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;

public record AiFormulaAnalysis(
		String cell, String formula, List<String> references,
		@JsonProperty("cached_value") Object cachedValue, String role,
		AiProvenance provenance) {
	public AiFormulaAnalysis(String cell, String formula, List<String> references,
			Object cachedValue, String role) {
		this(cell, formula, references, cachedValue, role, null);
	}

	public AiFormulaAnalysis(String cell, String formula, List<String> references) {
		this(cell, formula, references, null, "calculation", null);
	}
}
