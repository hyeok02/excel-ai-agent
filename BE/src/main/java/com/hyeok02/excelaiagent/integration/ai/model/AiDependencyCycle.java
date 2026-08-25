package com.hyeok02.excelaiagent.integration.ai.model;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;

public record AiDependencyCycle(
		String id, @JsonProperty("node_count") int nodeCount,
		@JsonProperty("edge_count") int edgeCount,
		@JsonProperty("sheet_names") List<String> sheetNames,
		List<AiDependencyNode> nodes, List<AiDependencyEdge> edges,
		@JsonProperty("is_truncated") Boolean truncated) {
}
