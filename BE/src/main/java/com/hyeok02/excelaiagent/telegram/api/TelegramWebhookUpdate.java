package com.hyeok02.excelaiagent.telegram.api;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public record TelegramWebhookUpdate(
		@JsonProperty("update_id") Long updateId,
		Message message) {

	@JsonIgnoreProperties(ignoreUnknown = true)
	public record Message(
			Long id,
			String text,
			Chat chat,
			User from) {
	}

	@JsonIgnoreProperties(ignoreUnknown = true)
	public record Chat(Long id, String type) {
	}

	@JsonIgnoreProperties(ignoreUnknown = true)
	public record User(
			Long id,
			String username,
			@JsonProperty("first_name") String firstName,
			@JsonProperty("last_name") String lastName) {
	}
}
