package com.hyeok02.excelaiagent.integration.ai;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonAlias;

public record AiWritebackProposal(
		String instruction,
		String status,
		String summary,
		List<Change> changes,
		List<String> risks,
		List<String> limitations) {

	public record Change(
			@JsonAlias("sheet_name") String sheetName,
			String reference,
			@JsonAlias("new_value") Object newValue,
			String reason,
			@JsonAlias("old_value") Object oldValue,
			@JsonAlias("context_cells") List<ContextCell> contextCells,
			@JsonAlias("change_type") String changeType,
			@JsonAlias("value_type") String valueType,
			@JsonAlias("affected_cells") List<String> affectedCells,
			@JsonAlias("risk_level") String riskLevel) {
		public Change(
				String sheetName, String reference, Object newValue, String reason,
				Object oldValue, List<ContextCell> contextCells) {
			this(sheetName, reference, newValue, reason, oldValue, contextCells,
					null, null, List.of(), null);
		}

		public record ContextCell(String reference, Object value) {}
	}

	public boolean blocked() {
		return !"ready".equalsIgnoreCase(status);
	}
}
