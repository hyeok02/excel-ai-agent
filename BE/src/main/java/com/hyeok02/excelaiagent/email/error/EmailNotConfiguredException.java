package com.hyeok02.excelaiagent.email.error;

public class EmailNotConfiguredException extends RuntimeException {
	public EmailNotConfiguredException() {
		super("이메일 전송 설정이 필요합니다.");
	}
}
