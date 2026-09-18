package com.hyeok02.excelaiagent.common.config;

import java.time.Duration;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.telegram")
public record TelegramProperties(
		boolean enabled,
		String botToken,
		String chatId,
		String webhookSecret,
		String webhookUrl,
		String baseUrl,
		Duration connectTimeout,
		Duration readTimeout,
		Duration invitationTtl) {

	public TelegramProperties {
		botToken = botToken == null ? "" : botToken.trim();
		chatId = chatId == null ? "" : chatId.trim();
		webhookSecret = webhookSecret == null ? "" : webhookSecret.trim();
		webhookUrl = webhookUrl == null ? "" : webhookUrl.trim();
		baseUrl = baseUrl == null || baseUrl.isBlank()
				? "https://api.telegram.org"
				: baseUrl.replaceAll("/+$", "");
		connectTimeout = connectTimeout == null ? Duration.ofSeconds(3) : connectTimeout;
		readTimeout = readTimeout == null ? Duration.ofSeconds(10) : readTimeout;
		invitationTtl = invitationTtl == null || invitationTtl.isZero()
				|| invitationTtl.isNegative() ? Duration.ofHours(24) : invitationTtl;
	}

	public boolean configured() {
		return botConfigured();
	}

	public boolean botConfigured() {
		return enabled && !botToken.isBlank();
	}

	public boolean webhookConfigured() {
		return botConfigured() && !webhookSecret.isBlank();
	}

	public boolean webhookRegistrationConfigured() {
		return webhookConfigured() && !webhookUrl.isBlank();
	}

	public boolean legacyConfigured() {
		return botConfigured() && !chatId.isBlank();
	}
}
