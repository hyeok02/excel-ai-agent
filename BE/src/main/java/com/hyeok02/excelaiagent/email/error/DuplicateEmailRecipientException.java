package com.hyeok02.excelaiagent.email.error;

public class DuplicateEmailRecipientException extends RuntimeException {
	public DuplicateEmailRecipientException() {
		super("이미 등록된 이메일 수신자입니다.");
	}
}
