package com.hyeok02.excelaiagent.telegram.application;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.hyeok02.excelaiagent.common.config.TelegramProperties;
import com.hyeok02.excelaiagent.telegram.api.TelegramWebhookUpdate;
import com.hyeok02.excelaiagent.telegram.error.TelegramWebhookUnauthorizedException;
import org.springframework.stereotype.Service;

@Service
public class TelegramWebhookService {
	private static final Pattern START_COMMAND = Pattern.compile(
			"^/start(?:@[A-Za-z0-9_]+)?\\s+([A-Za-z0-9_-]{20,})\\s*$");

	private final TelegramProperties properties;
	private final TelegramRecipientManagementService recipientService;

	public TelegramWebhookService(
			TelegramProperties properties,
			TelegramRecipientManagementService recipientService) {
		this.properties = properties;
		this.recipientService = recipientService;
	}

	public WebhookResult receive(String suppliedSecret, TelegramWebhookUpdate update) {
		verifySecret(suppliedSecret);
		if (update == null || update.message() == null
				|| update.message().chat() == null
				|| update.message().chat().id() == null
				|| !"private".equals(update.message().chat().type())
				|| update.message().from() == null
				|| update.message().from().id() == null
				|| update.message().text() == null) {
			return WebhookResult.IGNORED;
		}

		Matcher matcher = START_COMMAND.matcher(update.message().text().trim());
		if (!matcher.matches()) {
			return WebhookResult.IGNORED;
		}
		TelegramWebhookUpdate.User from = update.message().from();
		TelegramRecipientConnection connection = recipientService.connectFromInvitation(
				matcher.group(1), String.valueOf(update.message().chat().id()),
				String.valueOf(from.id()), from.username(), from.firstName(), from.lastName());
		recipientService.sendConnectionConfirmation(connection);
		return connection.status() == TelegramRecipientConnection.ConnectionStatus.CONNECTED
				? WebhookResult.CONNECTED : WebhookResult.INVALID_INVITATION;
	}

	private void verifySecret(String suppliedSecret) {
		if (!properties.webhookConfigured() || suppliedSecret == null
				|| !MessageDigest.isEqual(
						properties.webhookSecret().getBytes(StandardCharsets.UTF_8),
						suppliedSecret.getBytes(StandardCharsets.UTF_8))) {
			throw new TelegramWebhookUnauthorizedException();
		}
	}

	public enum WebhookResult {
		CONNECTED,
		INVALID_INVITATION,
		IGNORED
	}
}
