package com.hyeok02.excelaiagent.telegram.api;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record TelegramShareResponse(
		Instant sentAt,
		int requestedCount,
		int successCount,
		int failureCount,
		List<Delivery> deliveries) {

	public static TelegramShareResponse legacy(Instant sentAt) {
		return new TelegramShareResponse(
				sentAt, 1, 1, 0,
				List.of(new Delivery(null, "기본 수신자", true, null)));
	}

	public static TelegramShareResponse of(Instant sentAt, List<Delivery> deliveries) {
		int successCount = (int) deliveries.stream()
				.filter(Delivery::success).count();
		return new TelegramShareResponse(
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
