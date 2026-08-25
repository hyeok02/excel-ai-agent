package com.hyeok02.excelaiagent.integration.ai.model;

public record AiDependencyNode(
		String id, String label, String sheet, String cell, String kind, String formula) {
}
