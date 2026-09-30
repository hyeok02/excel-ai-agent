package com.hyeok02.excelaiagent.auth.error;

import java.util.UUID;

public class UserAccountNotFoundException extends RuntimeException {

	public UserAccountNotFoundException(UUID userId) {
		super("사용자를 찾을 수 없습니다: " + userId);
	}
}
