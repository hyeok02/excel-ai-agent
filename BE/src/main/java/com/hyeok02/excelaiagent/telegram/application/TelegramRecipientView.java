package com.hyeok02.excelaiagent.telegram.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipient;

public record TelegramRecipientView(
		UUID id,
		String displayName,
		String username,
		Instant connectedAt,
		String status) {

	public static TelegramRecipientView from(TelegramRecipient recipient) {
		return new TelegramRecipientView(
				recipient.getRecipientId(), recipient.getDisplayName(),
				recipient.getTelegramUsername(), recipient.getConnectedAt(), "ACTIVE");
	}
}
