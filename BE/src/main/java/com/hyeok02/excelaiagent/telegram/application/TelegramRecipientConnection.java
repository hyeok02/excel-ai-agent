package com.hyeok02.excelaiagent.telegram.application;

public record TelegramRecipientConnection(
		String chatId,
		String displayName,
		ConnectionStatus status) {

	public enum ConnectionStatus {
		CONNECTED,
		INVALID_INVITATION
	}
}
