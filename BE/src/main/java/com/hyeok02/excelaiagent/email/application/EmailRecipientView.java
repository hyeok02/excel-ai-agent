package com.hyeok02.excelaiagent.email.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.email.domain.EmailRecipient;

public record EmailRecipientView(
		UUID id,
		String displayName,
		String email,
		Instant createdAt,
		String status) {

	public static EmailRecipientView from(EmailRecipient recipient) {
		return new EmailRecipientView(
				recipient.getRecipientId(), recipient.getDisplayName(),
				recipient.getEmail(), recipient.getCreatedAt(), "ACTIVE");
	}
}
