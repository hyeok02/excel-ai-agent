package com.hyeok02.excelaiagent.integration.ai;

public class AiServiceUnavailableException extends RuntimeException {

	public AiServiceUnavailableException() {
		super("AI Service가 정상 상태가 아닙니다.");
	}

	public AiServiceUnavailableException(Throwable cause) {
		super("AI Service에 연결할 수 없습니다.", cause);
	}
}
