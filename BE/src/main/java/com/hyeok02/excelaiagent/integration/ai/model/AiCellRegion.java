package com.hyeok02.excelaiagent.integration.ai.model;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.hyeok02.excelaiagent.integration.ai.AiAnalysisInclusion;
import com.hyeok02.excelaiagent.integration.ai.AiSemanticClassification;

public record AiCellRegion(
		@JsonProperty("start_cell") String startCell,
		@JsonProperty("end_cell") String endCell,
		@JsonProperty("cell_count") int cellCount, String title,
		@JsonProperty("row_count") Integer rowCount,
		@JsonProperty("column_count") Integer columnCount,
		@JsonProperty("merged_ranges") List<String> mergedRanges,
		@JsonProperty("header_paths") List<AiHeaderPath> headerPaths,
		@JsonProperty("preview_rows") List<List<AiCellSnapshot>> previewRows,
		@JsonProperty("is_truncated") Boolean truncated,
		AiSemanticClassification semantic,
		@JsonProperty("analysis_inclusion") AiAnalysisInclusion analysisInclusion) {
	public AiCellRegion(String start, String end, int count, String title, Integer rows,
			Integer columns, List<String> merges, List<AiHeaderPath> headers,
			List<List<AiCellSnapshot>> previews, Boolean truncated) {
		this(start, end, count, title, rows, columns, merges, headers, previews, truncated, null, null);
	}
	public AiCellRegion(String start, String end, int count, String title, Integer rows,
			Integer columns, List<String> merges, List<AiHeaderPath> headers,
			List<List<AiCellSnapshot>> previews, Boolean truncated, AiSemanticClassification semantic) {
		this(start, end, count, title, rows, columns, merges, headers, previews, truncated, semantic, null);
	}
	public AiCellRegion(String start, String end, int count) {
		this(start, end, count, null, 0, 0, List.of(), List.of(), List.of(), false);
	}
	public AiCellRegion(String start, String end, int count,
			List<List<AiCellSnapshot>> previews, Boolean truncated) {
		this(start, end, count, null, 0, 0, List.of(), List.of(), previews, truncated);
	}
}
