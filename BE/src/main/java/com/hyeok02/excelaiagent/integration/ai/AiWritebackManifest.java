package com.hyeok02.excelaiagent.integration.ai;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonAlias;

public record AiWritebackManifest(
		@JsonAlias("changed_cells") List<String> changedCells,
		List<Check> checks,
		boolean verified) {
	public record Check(String name, boolean passed, String detail) {}
}
