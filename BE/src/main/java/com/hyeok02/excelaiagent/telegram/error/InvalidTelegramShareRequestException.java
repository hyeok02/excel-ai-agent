package com.hyeok02.excelaiagent.telegram.error;

public class InvalidTelegramShareRequestException extends RuntimeException {
	public InvalidTelegramShareRequestException() {
		super("전송할 텔레그램 수신자를 한 명 이상 선택해주세요.");
	}

	public InvalidTelegramShareRequestException(String message) {
		super(message);
	}
}
