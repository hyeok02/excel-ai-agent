package com.hyeok02.excelaiagent.email.error;

public class EmailDeliveryException extends RuntimeException {
	public EmailDeliveryException() {
		super("이메일을 전송하지 못했습니다.");
	}

	public EmailDeliveryException(Throwable cause) {
		super("이메일을 전송하지 못했습니다.", cause);
	}
}
