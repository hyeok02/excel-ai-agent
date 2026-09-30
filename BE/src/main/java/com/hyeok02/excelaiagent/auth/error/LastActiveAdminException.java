package com.hyeok02.excelaiagent.auth.error;

public class LastActiveAdminException extends RuntimeException {

	public LastActiveAdminException() {
		super("마지막 활성 관리자 계정은 비활성화할 수 없습니다.");
	}
}
