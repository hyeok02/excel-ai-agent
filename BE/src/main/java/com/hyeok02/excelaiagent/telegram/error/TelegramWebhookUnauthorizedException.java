package com.hyeok02.excelaiagent.telegram.error;

public class TelegramWebhookUnauthorizedException extends RuntimeException {
	public TelegramWebhookUnauthorizedException() {
		super("유효하지 않은 텔레그램 웹훅 요청입니다.");
	}
}
