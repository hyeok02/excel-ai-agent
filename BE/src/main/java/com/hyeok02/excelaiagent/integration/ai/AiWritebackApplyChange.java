package com.hyeok02.excelaiagent.integration.ai;

import com.fasterxml.jackson.annotation.JsonProperty;

record AiWritebackApplyChange(
		@JsonProperty("sheet_name") String sheetName,
		String reference,
		@JsonProperty("new_value") Object newValue,
		String reason,
		@JsonProperty("old_value") Object oldValue) {

	static AiWritebackApplyChange from(AiWritebackProposal.Change change) {
		return new AiWritebackApplyChange(
				change.sheetName(), change.reference(), change.newValue(),
				change.reason(), change.oldValue());
	}
}
