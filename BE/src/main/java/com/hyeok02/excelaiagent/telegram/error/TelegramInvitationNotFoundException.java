package com.hyeok02.excelaiagent.telegram.error;

public class TelegramInvitationNotFoundException extends RuntimeException {
	public TelegramInvitationNotFoundException() {
		super("텔레그램 초대를 찾을 수 없습니다.");
	}
}
