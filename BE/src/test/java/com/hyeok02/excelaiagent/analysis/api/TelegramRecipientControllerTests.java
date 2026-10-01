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

class TelegramRecipientControllerTests extends TelegramRecipientTestSupport {
	@Test
	void createsOneTimeInvitationAndStoresOnlyTokenHash() throws Exception {
		String body = mockMvc.perform(post("/api/v1/telegram/invitations")
					.with(user("alice"))
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"label\":\"재무팀 김대리\"}"))
				.andExpect(status().isCreated())
				.andExpect(jsonPath("$.status").value("ACTIVE"))
				.andExpect(jsonPath("$.inviteUrl", containsString(
						"https://t.me/excel_demo_bot?start=")))
				.andReturn().getResponse().getContentAsString();
		String inviteUrl = JsonPath.read(body, "$.inviteUrl");
		String rawToken = URI.create(inviteUrl).getQuery().substring("start=".length());

		Map<String, Object> stored = jdbcTemplate.queryForMap(
				"SELECT token_hash FROM telegram_recipient_invites");
		assertThat(stored.get("token_hash").toString())
				.hasSize(64)
				.doesNotContain(rawToken);

		mockMvc.perform(get("/api/v1/telegram/invitations").with(user("alice")))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$[0].label").value("재무팀 김대리"))
				.andExpect(jsonPath("$[0].inviteUrl").doesNotExist());
	}

	@Test
	void connectsPrivateChatOnceAndScopesRecipientToInvitationOwner() throws Exception {
		String token = createInvitation("alice", "홍길동");

		mockMvc.perform(post("/api/v1/telegram/webhook")
					.header("X-Telegram-Bot-Api-Secret-Token", "test-webhook-secret")
					.contentType(MediaType.APPLICATION_JSON)
					.content(webhook(token, "112233", "private", "hong")))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("CONNECTED"));

		mockMvc.perform(get("/api/v1/telegram/recipients").with(user("alice")))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$[0].displayName").value("홍길동"))
				.andExpect(jsonPath("$[0].username").value("hong"))
				.andExpect(jsonPath("$[0].status").value("ACTIVE"))
				.andExpect(jsonPath("$[0].chatId").doesNotExist());
		mockMvc.perform(get("/api/v1/telegram/recipients").with(user("bob")))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$").isEmpty());
		verify(telegramClient).sendMessage(eq("112233"), contains("연결되었습니다"));

		mockMvc.perform(post("/api/v1/telegram/webhook")
					.header("X-Telegram-Bot-Api-Secret-Token", "test-webhook-secret")
					.contentType(MediaType.APPLICATION_JSON)
					.content(webhook(token, "112233", "private", "hong")))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("INVALID_INVITATION"));
	}

	@Test
	void rejectsWrongWebhookSecretAndIgnoresGroupChats() throws Exception {
		String token = createInvitation("alice", null);
		mockMvc.perform(post("/api/v1/telegram/webhook")
					.header("X-Telegram-Bot-Api-Secret-Token", "wrong")
					.contentType(MediaType.APPLICATION_JSON)
					.content(webhook(token, "-1001", "private", "hong")))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("INVALID_TELEGRAM_WEBHOOK_SECRET"));

		mockMvc.perform(post("/api/v1/telegram/webhook")
					.header("X-Telegram-Bot-Api-Secret-Token", "test-webhook-secret")
					.contentType(MediaType.APPLICATION_JSON)
					.content(webhook(token, "-1001", "group", "hong")))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("IGNORED"));
		assertThat(recipientRepository.count()).isZero();
	}

	@Test
	void deactivatesOnlyOwnedRecipient() throws Exception {
		String token = createInvitation("alice", "홍길동");
		connect(token, "112233", "hong");
		String recipientId = JsonPath.read(mockMvc.perform(
				get("/api/v1/telegram/recipients").with(user("alice")))
				.andReturn().getResponse().getContentAsString(), "$[0].id");
		String analysisId = submit("deactivate.xlsx", "alice");
		IssuedAnalysisPublicShare share = publicShareService.issue(
				UUID.fromString(analysisId), UUID.fromString(recipientId), "alice");

		mockMvc.perform(delete("/api/v1/telegram/recipients/{id}", recipientId)
					.with(user("bob")))
				.andExpect(status().isNotFound());
		mockMvc.perform(delete("/api/v1/telegram/recipients/{id}", recipientId)
					.with(user("alice")))
				.andExpect(status().isNoContent());
		mockMvc.perform(get("/api/v1/telegram/recipients").with(user("alice")))
				.andExpect(jsonPath("$").isEmpty());
		assertThat(publicShareRepository.findById(share.shareId()))
				.get().extracting(AnalysisPublicShare::getRevokedAt).isNotNull();
	}
}
