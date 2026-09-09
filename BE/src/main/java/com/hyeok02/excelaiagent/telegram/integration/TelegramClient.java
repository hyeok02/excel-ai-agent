package com.hyeok02.excelaiagent.telegram.integration;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.hyeok02.excelaiagent.common.config.TelegramProperties;
import com.hyeok02.excelaiagent.telegram.error.TelegramDeliveryException;
import com.hyeok02.excelaiagent.telegram.error.TelegramNotConfiguredException;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class TelegramClient {
	private final RestClient restClient;
	private final TelegramProperties properties;

	public TelegramClient(
			@Qualifier("telegramRestClient") RestClient restClient,
			TelegramProperties properties) {
		this.restClient = restClient;
		this.properties = properties;
	}

	public void sendMessage(String text) {
		if (!properties.configured()) {
			throw new TelegramNotConfiguredException();
		}
		try {
			TelegramResponse response = restClient.post()
					.uri("/bot{token}/sendMessage", properties.botToken())
					.contentType(MediaType.APPLICATION_JSON)
					.body(new SendMessageRequest(
							properties.chatId(), text, new LinkPreviewOptions(true)))
					.retrieve()
					.body(TelegramResponse.class);
			if (response == null || !response.ok()) {
				throw new TelegramDeliveryException();
			}
		}
		catch (RestClientException exception) {
			throw new TelegramDeliveryException(exception);
		}
	}

	private record SendMessageRequest(
			@JsonProperty("chat_id") String chatId,
			String text,
			@JsonProperty("link_preview_options") LinkPreviewOptions linkPreviewOptions) {
	}

	private record LinkPreviewOptions(@JsonProperty("is_disabled") boolean disabled) {
	}

	private record TelegramResponse(boolean ok) {
	}
}
