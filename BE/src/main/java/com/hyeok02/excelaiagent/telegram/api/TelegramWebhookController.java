package com.hyeok02.excelaiagent.telegram.api;

import com.hyeok02.excelaiagent.telegram.application.TelegramWebhookService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/telegram/webhook")
public class TelegramWebhookController {
	private final TelegramWebhookService webhookService;

	public TelegramWebhookController(TelegramWebhookService webhookService) {
		this.webhookService = webhookService;
	}

	@PostMapping
	public WebhookResponse receive(
			@RequestHeader(name = "X-Telegram-Bot-Api-Secret-Token", required = false)
			String secret,
			@RequestBody(required = false) TelegramWebhookUpdate update) {
		return new WebhookResponse(webhookService.receive(secret, update).name());
	}

	public record WebhookResponse(String status) {
	}
}
