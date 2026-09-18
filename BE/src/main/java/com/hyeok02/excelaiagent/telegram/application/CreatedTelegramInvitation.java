package com.hyeok02.excelaiagent.telegram.application;

import java.time.Instant;
import java.util.UUID;

public record CreatedTelegramInvitation(
		UUID id,
		String label,
		String inviteUrl,
		Instant createdAt,
		Instant expiresAt,
		String status) {
}
