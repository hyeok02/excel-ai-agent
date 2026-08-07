package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;

public record AnalysisDetails(
		UUID analysisId,
		AnalysisStatus status,
		AnalysisMode mode,
		String originalFilename,
		String fileExtension,
		long sizeBytes,
		Instant createdAt,
		Instant updatedAt) {
}
