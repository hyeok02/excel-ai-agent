package com.hyeok02.excelaiagent.telegram.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientInvitation;

public record TelegramInvitationView(
		UUID id,
		String label,
		Instant createdAt,
		Instant expiresAt,
		String status) {

	public static TelegramInvitationView from(
			TelegramRecipientInvitation invitation, Instant now) {
		return new TelegramInvitationView(
				invitation.getInvitationId(), invitation.getLabel(),
				invitation.getCreatedAt(), invitation.getExpiresAt(),
				invitation.status(now).name());
	}
}
