package com.hyeok02.excelaiagent.email.api;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record EmailShareResponse(
		Instant sentAt,
		int requestedCount,
		int successCount,
		int failureCount,
		List<Delivery> deliveries) {

	public static EmailShareResponse of(Instant sentAt, List<Delivery> deliveries) {
		int successCount = (int) deliveries.stream()
				.filter(Delivery::success).count();
		return new EmailShareResponse(
				sentAt, deliveries.size(), successCount,
				deliveries.size() - successCount, List.copyOf(deliveries));
	}

	public record Delivery(
			UUID recipientId,
			String recipientName,
			boolean success,
			String errorMessage) {
	}
}
