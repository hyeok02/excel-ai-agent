package com.hyeok02.excelaiagent.analysis.error;

/** 분석 대기열이 가득 차 접수를 받지 못했다. */
public class AnalysisQueueFullException extends RuntimeException {
	public AnalysisQueueFullException(Throwable cause) {
		super("지금은 분석 요청이 밀려 있어 접수하지 못했습니다. 잠시 후 다시 시도해주세요.", cause);
	}
}
