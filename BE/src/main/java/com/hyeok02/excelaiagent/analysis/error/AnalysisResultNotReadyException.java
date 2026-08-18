package com.hyeok02.excelaiagent.analysis.error;

import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;

public class AnalysisResultNotReadyException extends RuntimeException {

	public AnalysisResultNotReadyException(UUID analysisId, AnalysisStatus status) {
		super("분석 결과가 아직 준비되지 않았습니다: %s (status=%s)".formatted(analysisId, status));
	}
}
