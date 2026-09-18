package com.hyeok02.excelaiagent.telegram.integration;

import com.hyeok02.excelaiagent.common.config.TelegramProperties;
import com.hyeok02.excelaiagent.telegram.error.TelegramDeliveryException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

@Component
public class TelegramWebhookInitializer implements ApplicationRunner {
	private static final Logger log = LoggerFactory.getLogger(TelegramWebhookInitializer.class);

	private final TelegramProperties properties;
	private final TelegramClient telegramClient;

	public TelegramWebhookInitializer(
			TelegramProperties properties, TelegramClient telegramClient) {
		this.properties = properties;
		this.telegramClient = telegramClient;
	}

	@Override
	public void run(ApplicationArguments args) {
		if (!properties.webhookRegistrationConfigured()) {
			return;
		}
		try {
			telegramClient.setWebhook(properties.webhookUrl(), properties.webhookSecret());
			log.info("Telegram webhook registration completed");
		}
		catch (TelegramDeliveryException exception) {
			// Telegram availability must not prevent the analysis service from starting.
			// Do not log the RestClient cause because its request URL contains the bot token.
			log.error("Telegram webhook registration failed; verify configuration and connectivity");
		}
	}
}
