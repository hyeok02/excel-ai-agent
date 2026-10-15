package com.hyeok02.excelaiagent.integration.ai;

public class AiServiceUnavailableException extends RuntimeException {
	public static final String QUOTA_MESSAGE =
			"AI 서비스 사용 한도가 소진되어 답변을 생성할 수 없습니다. 관리자가 API 이용 한도를 확인해야 합니다.";
	private final boolean quotaExceeded;

	public AiServiceUnavailableException() {
		super("AI Service가 정상 상태가 아닙니다.");
		quotaExceeded = false;
	}

	public AiServiceUnavailableException(Throwable cause) {
		super("AI Service에 연결할 수 없습니다.", cause);
		quotaExceeded = false;
	}

	private AiServiceUnavailableException(boolean quotaExceeded) {
		super(QUOTA_MESSAGE);
		this.quotaExceeded = quotaExceeded;
	}

	public static AiServiceUnavailableException quotaExceeded() {
		return new AiServiceUnavailableException(true);
	}

	public final String userMessage() {
		return quotaExceeded ? QUOTA_MESSAGE : "AI 응답을 생성하지 못했습니다. 잠시 후 다시 시도해주세요.";
	}
}
