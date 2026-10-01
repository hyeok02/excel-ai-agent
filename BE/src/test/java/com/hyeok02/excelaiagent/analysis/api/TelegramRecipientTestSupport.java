package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.net.URI;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.hyeok02.excelaiagent.sharing.application.AnalysisPublicShareService;
import com.hyeok02.excelaiagent.sharing.application.IssuedAnalysisPublicShare;
import com.hyeok02.excelaiagent.sharing.domain.AnalysisPublicShare;
import com.hyeok02.excelaiagent.sharing.domain.AnalysisPublicShareRepository;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientInvitationRepository;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientRepository;
import com.hyeok02.excelaiagent.telegram.error.TelegramDeliveryException;
import com.hyeok02.excelaiagent.telegram.error.TelegramNotConfiguredException;
import com.hyeok02.excelaiagent.telegram.integration.TelegramClient;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

/** 텔레그램 수신자 테스트가 함께 쓰는 준비와 보조 메서드. */
@TestPropertySource(properties = {
		"app.telegram.enabled=true",
		"app.telegram.bot-token=test-token",
		"app.telegram.chat-id=legacy-chat",
		"app.telegram.webhook-secret=test-webhook-secret",
		"app.telegram.invitation-ttl=24h"
})
abstract class TelegramRecipientTestSupport extends AnalysisControllerTestSupport {
	@MockitoBean TelegramClient telegramClient;

	@Autowired TelegramRecipientRepository recipientRepository;

	@Autowired TelegramRecipientInvitationRepository invitationRepository;

	@Autowired AnalysisPublicShareRepository publicShareRepository;

	@Autowired AnalysisPublicShareService publicShareService;

	@Autowired JdbcTemplate jdbcTemplate;

	@BeforeEach
	void prepareTelegram() {
		publicShareRepository.deleteAll();
		invitationRepository.deleteAll();
		recipientRepository.deleteAll();
		reset(telegramClient);
		when(telegramClient.getBotUsername()).thenReturn("excel_demo_bot");
	}

	protected String createInvitation(String owner, String label) throws Exception {
		String content = label == null ? "{}" : "{\"label\":\"%s\"}".formatted(label);
		String body = mockMvc.perform(post("/api/v1/telegram/invitations")
					.with(user(owner)).contentType(MediaType.APPLICATION_JSON).content(content))
				.andReturn().getResponse().getContentAsString();
		String inviteUrl = JsonPath.read(body, "$.inviteUrl");
		return URI.create(inviteUrl).getQuery().substring("start=".length());
	}

	protected void connect(String token, String chatId, String username) throws Exception {
		mockMvc.perform(post("/api/v1/telegram/webhook")
					.header("X-Telegram-Bot-Api-Secret-Token", "test-webhook-secret")
					.contentType(MediaType.APPLICATION_JSON)
					.content(webhook(token, chatId, "private", username)))
				.andExpect(status().isOk());
	}

	protected String connectAndGetRecipientId(
			String owner, String label, String chatId, String username) throws Exception {
		connect(createInvitation(owner, label), chatId, username);
		String body = mockMvc.perform(get("/api/v1/telegram/recipients").with(user(owner)))
				.andReturn().getResponse().getContentAsString();
		java.util.List<String> ids = JsonPath.read(
				body, "$[?(@.displayName == '%s')].id".formatted(label));
		return ids.getFirst();
	}

	protected String webhook(String token, String chatId, String type, String username) {
		return """
				{
				  "update_id": 1,
				  "message": {
				    "text": "/start %s",
				    "chat": {"id": %s, "type": "%s"},
				    "from": {"id": 77, "username": "%s", "first_name": "Telegram"}
				  }
				}
				""".formatted(token, chatId, type, username);
	}

	protected String submit(String filename, String owner) throws Exception {
		String body = mockMvc.perform(multipart("/api/v1/analyses")
					.file(excel(filename)).param("mode", "LLM").with(user(owner)))
				.andReturn().getResponse().getContentAsString();
		return JsonPath.read(body, "$.analysisId");
	}
}
