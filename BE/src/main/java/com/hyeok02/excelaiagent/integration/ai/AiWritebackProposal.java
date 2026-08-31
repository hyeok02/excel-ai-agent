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
			@JsonAlias("old_value") Object oldValue) {}

	public boolean blocked() {
		return !"ready".equalsIgnoreCase(status);
	}
}
