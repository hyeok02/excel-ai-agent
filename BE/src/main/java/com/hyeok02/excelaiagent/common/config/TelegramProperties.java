package com.hyeok02.excelaiagent.common.config;

import java.time.Duration;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.telegram")
public record TelegramProperties(
		boolean enabled,
		String botToken,
		String chatId,
		String baseUrl,
		Duration connectTimeout,
		Duration readTimeout) {

	public TelegramProperties {
		botToken = botToken == null ? "" : botToken.trim();
		chatId = chatId == null ? "" : chatId.trim();
		baseUrl = baseUrl == null || baseUrl.isBlank()
				? "https://api.telegram.org"
				: baseUrl.replaceAll("/+$", "");
		connectTimeout = connectTimeout == null ? Duration.ofSeconds(3) : connectTimeout;
		readTimeout = readTimeout == null ? Duration.ofSeconds(10) : readTimeout;
	}

	public boolean configured() {
		return enabled && !botToken.isBlank() && !chatId.isBlank();
	}
}
