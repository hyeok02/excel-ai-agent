package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;

public record AnalysisSubmission(
		UUID analysisId,
		AnalysisStatus status,
		AnalysisMode mode,
		String originalFilename,
		long sizeBytes,
		Instant createdAt) {
}
