package com.hyeok02.excelaiagent.analysis.error;

import java.util.UUID;

public class AnalysisSourceUnavailableException extends RuntimeException {

	public AnalysisSourceUnavailableException(UUID analysisId) {
		super("원본 파일 보관기간이 지나 질문과 Excel 수정 기능을 사용할 수 없습니다: "
				+ analysisId);
	}
}
