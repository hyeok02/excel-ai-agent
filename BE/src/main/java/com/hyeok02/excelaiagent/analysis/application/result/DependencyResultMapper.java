package com.hyeok02.excelaiagent.analysis.application.result;

import java.util.List;
import com.hyeok02.excelaiagent.integration.ai.model.AiDependencyCluster;
import com.hyeok02.excelaiagent.integration.ai.model.AiDependencyCycle;
import com.hyeok02.excelaiagent.integration.ai.model.AiDependencyEdge;
import com.hyeok02.excelaiagent.integration.ai.model.AiDependencyNode;
import com.hyeok02.excelaiagent.integration.ai.model.AiDependencySummary;

final class DependencyResultMapper {
	private DependencyResultMapper() {
	}

	static AnalysisDependencyResult.Graph map(AiDependencySummary summary) {
		if (summary == null) {
			return new AnalysisDependencyResult.Graph(0, 0, 0, 0, 0, 0, 0, List.of(), 0, 0, List.of());
		}
		return new AnalysisDependencyResult.Graph(
				summary.nodeCount(), summary.edgeCount(), summary.formulaNodeCount(),
				summary.crossSheetEdgeCount(), summary.namedReferenceCount(),
				summary.externalReferenceCount(), summary.clusterCount(),
				SemanticResultMapper.safe(summary.clusters()).stream().map(DependencyResultMapper::map).toList(),
				summary.cycleCount(), summary.cyclicNodeCount(),
				SemanticResultMapper.safe(summary.cycles()).stream().map(DependencyResultMapper::map).toList());
	}

	private static AnalysisDependencyResult.Cluster map(AiDependencyCluster cluster) {
		return new AnalysisDependencyResult.Cluster(
				cluster.id(), cluster.nodeCount(), cluster.edgeCount(), cluster.formulaCount(),
				SemanticResultMapper.safe(cluster.sheetNames()),
				SemanticResultMapper.safe(cluster.nodes()).stream().map(DependencyResultMapper::map).toList(),
				SemanticResultMapper.safe(cluster.edges()).stream().map(DependencyResultMapper::map).toList(),
				Boolean.TRUE.equals(cluster.truncated()));
	}

	private static AnalysisDependencyResult.Cycle map(AiDependencyCycle cycle) {
		return new AnalysisDependencyResult.Cycle(
				cycle.id(), cycle.nodeCount(), cycle.edgeCount(),
				SemanticResultMapper.safe(cycle.sheetNames()),
				SemanticResultMapper.safe(cycle.nodes()).stream().map(DependencyResultMapper::map).toList(),
				SemanticResultMapper.safe(cycle.edges()).stream().map(DependencyResultMapper::map).toList(),
				Boolean.TRUE.equals(cycle.truncated()));
	}

	private static AnalysisDependencyResult.Node map(AiDependencyNode node) {
		return new AnalysisDependencyResult.Node(
				node.id(), node.label(), node.sheet(), node.cell(), node.kind(), node.formula());
	}

	private static AnalysisDependencyResult.Edge map(AiDependencyEdge edge) {
		return new AnalysisDependencyResult.Edge(
				edge.source(), edge.target(), edge.reference(), edge.crossSheet());
	}
}
