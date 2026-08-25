package com.hyeok02.excelaiagent.integration.ai.model;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;

public record AiDependencySummary(
		@JsonProperty("node_count") int nodeCount,
		@JsonProperty("edge_count") int edgeCount,
		@JsonProperty("formula_node_count") int formulaNodeCount,
		@JsonProperty("cross_sheet_edge_count") int crossSheetEdgeCount,
		@JsonProperty("named_reference_count") int namedReferenceCount,
		@JsonProperty("external_reference_count") int externalReferenceCount,
		@JsonProperty("cluster_count") int clusterCount,
		List<AiDependencyCluster> clusters,
		@JsonProperty("cycle_count") int cycleCount,
		@JsonProperty("cyclic_node_count") int cyclicNodeCount,
		List<AiDependencyCycle> cycles) {
}
