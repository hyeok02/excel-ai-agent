package com.hyeok02.excelaiagent.analysis.error;

import java.util.UUID;

public class AnalysisNotFoundException extends RuntimeException {

	public AnalysisNotFoundException(UUID analysisId) {
		super("분석 작업을 찾을 수 없습니다: " + analysisId);
	}
}
