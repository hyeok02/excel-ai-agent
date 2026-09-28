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
			@JsonAlias("risk_level") String riskLevel,
			@JsonAlias("related_cells") List<RelatedCell> relatedCells,
			String derivation) {
		public Change(
				String sheetName, String reference, Object newValue, String reason,
				Object oldValue, List<ContextCell> contextCells) {
			this(sheetName, reference, newValue, reason, oldValue, contextCells,
					null, null, List.of(), null, List.of(), null);
		}

		public Change(
				String sheetName, String reference, Object newValue, String reason,
				Object oldValue, List<ContextCell> contextCells, String changeType,
				String valueType, List<String> affectedCells, String riskLevel) {
			this(sheetName, reference, newValue, reason, oldValue, contextCells,
					changeType, valueType, affectedCells, riskLevel, List.of(), null);
		}

		/** 예전에 저장한 제안 JSON에는 이 항목이 없어 null로 들어온다. */
		@Override
		public List<RelatedCell> relatedCells() {
			return relatedCells == null ? List.of() : relatedCells;
		}

		public record ContextCell(String reference, Object value) {}

		/** 수식으로 이어져 있지 않아 함께 확인해야 하는 셀. */
		public record RelatedCell(
				@JsonAlias("sheet_name") String sheetName,
				String reference,
				@JsonAlias("current_value") Object currentValue,
				@JsonAlias("suggested_value") Object suggestedValue,
				String kind,
				String reason,
				List<String> breakdown,
				List<String> parts) {

			/** 합계 셀이 아니면 비어 있고, 예전에 저장한 제안에는 아예 없다. */
			public RelatedCell(
					String sheetName, String reference, Object currentValue,
					Object suggestedValue, String kind, String reason) {
				this(sheetName, reference, currentValue, suggestedValue, kind, reason,
						List.of(), List.of());
			}

			@Override
			public List<String> breakdown() {
				return breakdown == null ? List.of() : breakdown;
			}

			@Override
			public List<String> parts() {
				return parts == null ? List.of() : parts;
			}
		}
	}

	public boolean blocked() {
		return !"ready".equalsIgnoreCase(status);
	}
}
