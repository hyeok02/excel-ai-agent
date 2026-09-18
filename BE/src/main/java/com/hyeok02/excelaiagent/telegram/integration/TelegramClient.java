package com.hyeok02.excelaiagent.telegram.integration;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
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
	private volatile String cachedBotUsername;

	public TelegramClient(
			@Qualifier("telegramRestClient") RestClient restClient,
			TelegramProperties properties) {
		this.restClient = restClient;
		this.properties = properties;
	}

	public void sendMessage(String text) {
		if (!properties.legacyConfigured()) {
			throw new TelegramNotConfiguredException();
		}
		sendMessage(properties.chatId(), text);
	}

	public void sendMessage(String chatId, String text) {
		requireBot();
		if (chatId == null || chatId.isBlank()) {
			throw new TelegramDeliveryException();
		}
		try {
			TelegramOkResponse response = restClient.post()
					.uri("/bot{token}/sendMessage", properties.botToken())
					.contentType(MediaType.APPLICATION_JSON)
					.body(new SendMessageRequest(
							chatId, text, new LinkPreviewOptions(true)))
					.retrieve()
					.body(TelegramOkResponse.class);
			ensureOk(response);
		}
		catch (RestClientException exception) {
			throw new TelegramDeliveryException(exception);
		}
	}

	public String getBotUsername() {
		requireBot();
		String cached = cachedBotUsername;
		if (cached != null) {
			return cached;
		}
		synchronized (this) {
			if (cachedBotUsername == null) {
				cachedBotUsername = fetchBotUsername();
			}
			return cachedBotUsername;
		}
	}

	public void setWebhook(String webhookUrl, String secretToken) {
		requireBot();
		try {
			TelegramOkResponse response = restClient.post()
					.uri("/bot{token}/setWebhook", properties.botToken())
					.contentType(MediaType.APPLICATION_JSON)
					.body(new SetWebhookRequest(
							webhookUrl, secretToken, List.of("message")))
					.retrieve()
					.body(TelegramOkResponse.class);
			ensureOk(response);
		}
		catch (RestClientException exception) {
			throw new TelegramDeliveryException(exception);
		}
	}

	private String fetchBotUsername() {
		try {
			TelegramGetMeResponse response = restClient.get()
					.uri("/bot{token}/getMe", properties.botToken())
					.retrieve()
					.body(TelegramGetMeResponse.class);
			if (response == null || !response.ok() || response.result() == null
					|| response.result().username() == null
					|| response.result().username().isBlank()) {
				throw new TelegramDeliveryException();
			}
			return response.result().username().replaceFirst("^@", "");
		}
		catch (RestClientException exception) {
			throw new TelegramDeliveryException(exception);
		}
	}

	private void requireBot() {
		if (!properties.botConfigured()) {
			throw new TelegramNotConfiguredException();
		}
	}

	private void ensureOk(TelegramOkResponse response) {
		if (response == null || !response.ok()) {
			throw new TelegramDeliveryException();
		}
	}

	private record SendMessageRequest(
			@JsonProperty("chat_id") String chatId,
			String text,
			@JsonProperty("link_preview_options") LinkPreviewOptions linkPreviewOptions) {
	}

	private record LinkPreviewOptions(@JsonProperty("is_disabled") boolean disabled) {
	}

	private record SetWebhookRequest(
			String url,
			@JsonProperty("secret_token") String secretToken,
			@JsonProperty("allowed_updates") List<String> allowedUpdates) {
	}

	@JsonIgnoreProperties(ignoreUnknown = true)
	private record TelegramOkResponse(boolean ok) {
	}

	@JsonIgnoreProperties(ignoreUnknown = true)
	private record TelegramGetMeResponse(boolean ok, BotInfo result) {
	}

	@JsonIgnoreProperties(ignoreUnknown = true)
	private record BotInfo(String username) {
	}
}
