package com.hyeok02.excelaiagent.analysis.application.result;

import java.util.List;

public final class AnalysisDependencyResult {
	private AnalysisDependencyResult() {
	}

	public record Graph(
			int nodeCount, int edgeCount, int formulaNodeCount, int crossSheetEdgeCount,
			int namedReferenceCount, int externalReferenceCount, int clusterCount,
			List<Cluster> clusters, int cycleCount, int cyclicNodeCount, List<Cycle> cycles) {
	}

	public record Cluster(
			String id, int nodeCount, int edgeCount, int formulaCount,
			List<String> sheetNames, List<Node> nodes, List<Edge> edges, boolean truncated) {
	}

	public record Cycle(
			String id, int nodeCount, int edgeCount, List<String> sheetNames,
			List<Node> nodes, List<Edge> edges, boolean truncated) {
	}

	public record Node(
			String id, String label, String sheet, String cell, String kind, String formula) {
	}

	public record Edge(String source, String target, String reference, boolean crossSheet) {
	}
}
