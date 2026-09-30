package com.hyeok02.excelaiagent.auth.error;

public class SelfDeactivationException extends RuntimeException {

	public SelfDeactivationException() {
		super("현재 로그인한 계정은 비활성화할 수 없습니다.");
	}
}
