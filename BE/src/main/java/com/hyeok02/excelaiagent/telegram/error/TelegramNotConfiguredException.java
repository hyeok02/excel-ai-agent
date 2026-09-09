package com.hyeok02.excelaiagent.telegram.error;

public class TelegramNotConfiguredException extends RuntimeException {
	public TelegramNotConfiguredException() {
		super("텔레그램 전송 설정이 필요합니다.");
	}
}
