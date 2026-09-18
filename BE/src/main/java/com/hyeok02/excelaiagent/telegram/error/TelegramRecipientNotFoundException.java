package com.hyeok02.excelaiagent.telegram.error;

public class TelegramRecipientNotFoundException extends RuntimeException {
	public TelegramRecipientNotFoundException() {
		super("텔레그램 수신자를 찾을 수 없습니다.");
	}
}
