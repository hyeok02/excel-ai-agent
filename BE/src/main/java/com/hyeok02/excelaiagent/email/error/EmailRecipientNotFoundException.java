package com.hyeok02.excelaiagent.email.error;

public class EmailRecipientNotFoundException extends RuntimeException {
	public EmailRecipientNotFoundException() {
		super("이메일 수신자를 찾을 수 없습니다.");
	}
}
