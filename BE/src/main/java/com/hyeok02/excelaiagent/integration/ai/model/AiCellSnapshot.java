package com.hyeok02.excelaiagent.integration.ai.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.hyeok02.excelaiagent.integration.ai.AiSemanticClassification;

public record AiCellSnapshot(
		String address, Object value, String formula,
		@JsonProperty("cached_value") Object cachedValue,
		@JsonProperty("number_format") String numberFormat, Boolean bold,
		@JsonProperty("fill_color") String fillColor,
		@JsonProperty("horizontal_alignment") String horizontalAlignment,
		Boolean merged, AiSemanticClassification semantic) {
	public AiCellSnapshot(String address, Object value, String formula, Object cachedValue,
			String numberFormat, Boolean bold, String fillColor,
			String horizontalAlignment, Boolean merged) {
		this(address, value, formula, cachedValue, numberFormat, bold,
				fillColor, horizontalAlignment, merged, null);
	}
	public AiCellSnapshot(String address, Object value, String formula) {
		this(address, value, formula, null, null, false, null, null, false);
	}
}
