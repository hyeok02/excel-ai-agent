package com.hyeok02.excelaiagent.email.error;

public class InvalidEmailShareRequestException extends RuntimeException {
	public InvalidEmailShareRequestException() {
		super("전송할 이메일 수신자를 한 명 이상 선택해주세요.");
	}

	public InvalidEmailShareRequestException(String message) {
		super(message);
	}
}
