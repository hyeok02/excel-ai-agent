package com.hyeok02.excelaiagent.integration.ai.model;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;

public record AiTableSummary(
		String name, @JsonProperty("display_name") String displayName, String reference,
		List<String> headers, @JsonProperty("row_count") int rowCount,
		@JsonProperty("column_count") int columnCount,
		@JsonProperty("preview_rows") List<List<AiCellSnapshot>> previewRows,
		@JsonProperty("is_truncated") Boolean truncated) {
}
