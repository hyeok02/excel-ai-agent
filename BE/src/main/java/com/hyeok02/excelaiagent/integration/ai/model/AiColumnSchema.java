package com.hyeok02.excelaiagent.integration.ai.model;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;

public record AiColumnSchema(
		String column,
		@JsonProperty("source_range") String sourceRange,
		@JsonProperty("header_path") List<String> headerPath,
		@JsonProperty("display_name") String displayName,
		@JsonProperty("standard_field") String standardField,
		@JsonProperty("data_type") String dataType,
		@JsonProperty("unit_type") String unitType,
		@JsonProperty("unit_label") String unitLabel,
		double confidence,
		List<String> evidence,
		AiProvenance provenance) {
	public AiColumnSchema(
			String column, String sourceRange, List<String> headerPath,
			String displayName, String standardField, String dataType,
			String unitType, String unitLabel, double confidence,
			List<String> evidence) {
		this(column, sourceRange, headerPath, displayName, standardField,
				dataType, unitType, unitLabel, confidence, evidence, null);
	}
}
