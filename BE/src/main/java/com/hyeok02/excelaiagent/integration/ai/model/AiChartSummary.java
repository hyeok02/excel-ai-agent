package com.hyeok02.excelaiagent.integration.ai.model;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;

public record AiChartSummary(
		String title, @JsonProperty("chart_type") String chartType,
		@JsonProperty("anchor_cell") String anchorCell,
		@JsonProperty("series_count") int seriesCount,
		List<AiChartSeriesSummary> series,
		@JsonProperty("is_truncated") Boolean truncated) {
}
