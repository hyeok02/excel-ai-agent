package com.hyeok02.excelaiagent.telegram.error;

public class InvalidTelegramInvitationException extends RuntimeException {
	public InvalidTelegramInvitationException() {
		super("만료되었거나 이미 사용된 텔레그램 초대입니다.");
	}
}
