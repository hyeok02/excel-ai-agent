package com.hyeok02.excelaiagent.integration.ai.model;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;

public record AiChartSeriesSummary(
		String title,
		@JsonProperty("categories_reference") String categoriesReference,
		@JsonProperty("values_reference") String valuesReference,
		@JsonProperty("category_samples") List<Object> categorySamples,
		@JsonProperty("value_samples") List<Object> valueSamples) {
}
