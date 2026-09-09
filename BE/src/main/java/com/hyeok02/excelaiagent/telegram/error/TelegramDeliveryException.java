package com.hyeok02.excelaiagent.telegram.error;

public class TelegramDeliveryException extends RuntimeException {
	public TelegramDeliveryException() {
		super("텔레그램 메시지를 전송하지 못했습니다.");
	}

	public TelegramDeliveryException(Throwable cause) {
		super("텔레그램 메시지를 전송하지 못했습니다.", cause);
	}
}
