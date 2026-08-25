package com.hyeok02.excelaiagent.integration.ai.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiDependencyEdge(
		String source, String target, String reference,
		@JsonProperty("cross_sheet") boolean crossSheet) {
}
