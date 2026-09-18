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

@TestPropertySource(properties = {
		"app.telegram.enabled=true",
		"app.telegram.bot-token=test-token",
		"app.telegram.chat-id=legacy-chat",
		"app.telegram.webhook-secret=test-webhook-secret",
		"app.telegram.invitation-ttl=24h"
})
class TelegramRecipientControllerTests extends AnalysisControllerTestSupport {
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

	@Test
	void sharesToSelectedRecipientsAndReportsPartialFailure() throws Exception {
		String firstId = connectAndGetRecipientId("alice", "첫 번째", "111", "first");
		String secondId = connectAndGetRecipientId("alice", "두 번째", "222", "second");
		String analysisId = submit("sales.xlsx", "alice");
		reset(telegramClient);
		doThrow(new TelegramDeliveryException()).when(telegramClient)
				.sendMessage(eq("222"), anyString());

		mockMvc.perform(post("/api/v1/analyses/{id}/shares/telegram", analysisId)
					.with(user("alice"))
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"recipientIds\":[\"%s\",\"%s\"]}"
							.formatted(firstId, secondId)))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.requestedCount").value(2))
				.andExpect(jsonPath("$.successCount").value(1))
				.andExpect(jsonPath("$.failureCount").value(1))
				.andExpect(jsonPath("$.deliveries[0].success").value(true))
				.andExpect(jsonPath("$.deliveries[1].success").value(false));

		List<AnalysisPublicShare> shares = publicShareRepository.findAll();
		assertThat(shares).hasSize(2);
		assertThat(shares).filteredOn(share -> share.getRevokedAt() == null)
				.singleElement().extracting(AnalysisPublicShare::getRecipientId)
				.isEqualTo(UUID.fromString(firstId));
		assertThat(shares).filteredOn(share -> share.getRevokedAt() != null)
				.singleElement().extracting(AnalysisPublicShare::getRecipientId)
				.isEqualTo(UUID.fromString(secondId));
		ArgumentCaptor<String> deliveredMessage = ArgumentCaptor.forClass(String.class);
		verify(telegramClient).sendMessage(eq("111"), deliveredMessage.capture());
		assertThat(deliveredMessage.getValue())
				.contains("/shared/analysis/")
				.doesNotContain("/excel-analysis?id=");
	}

	@Test
	void rejectsExplicitEmptySelectionButKeepsLegacyNoBodyFallback() throws Exception {
		String analysisId = submit("sales.xlsx", "alice");
		mockMvc.perform(post("/api/v1/analyses/{id}/shares/telegram", analysisId)
					.with(user("alice"))
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"recipientIds\":[]}"))
				.andExpect(status().isBadRequest());

		mockMvc.perform(post("/api/v1/analyses/{id}/shares/telegram", analysisId)
					.with(user("alice")))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.deliveries[0].recipientName").value("기본 수신자"));
		verify(telegramClient).sendMessage(anyString());
	}

	@Test
	void revokesIssuedLinkWhenDeliveryAbortsWithAnUnexpectedTelegramFailure() throws Exception {
		String recipientId = connectAndGetRecipientId(
				"alice", "설정 오류 수신자", "333", "unconfigured");
		String analysisId = submit("sales.xlsx", "alice");
		reset(telegramClient);
		doThrow(new TelegramNotConfiguredException()).when(telegramClient)
				.sendMessage(eq("333"), anyString());

		mockMvc.perform(post("/api/v1/analyses/{id}/shares/telegram", analysisId)
					.with(user("alice"))
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"recipientIds\":[\"%s\"]}".formatted(recipientId)))
				.andExpect(status().isServiceUnavailable())
				.andExpect(jsonPath("$.code").value("TELEGRAM_NOT_CONFIGURED"));

		assertThat(publicShareRepository.findAll()).singleElement()
				.extracting(AnalysisPublicShare::getRevokedAt).isNotNull();
	}

	private String createInvitation(String owner, String label) throws Exception {
		String content = label == null ? "{}" : "{\"label\":\"%s\"}".formatted(label);
		String body = mockMvc.perform(post("/api/v1/telegram/invitations")
					.with(user(owner)).contentType(MediaType.APPLICATION_JSON).content(content))
				.andReturn().getResponse().getContentAsString();
		String inviteUrl = JsonPath.read(body, "$.inviteUrl");
		return URI.create(inviteUrl).getQuery().substring("start=".length());
	}

	private void connect(String token, String chatId, String username) throws Exception {
		mockMvc.perform(post("/api/v1/telegram/webhook")
					.header("X-Telegram-Bot-Api-Secret-Token", "test-webhook-secret")
					.contentType(MediaType.APPLICATION_JSON)
					.content(webhook(token, chatId, "private", username)))
				.andExpect(status().isOk());
	}

	private String connectAndGetRecipientId(
			String owner, String label, String chatId, String username) throws Exception {
		connect(createInvitation(owner, label), chatId, username);
		String body = mockMvc.perform(get("/api/v1/telegram/recipients").with(user(owner)))
				.andReturn().getResponse().getContentAsString();
		java.util.List<String> ids = JsonPath.read(
				body, "$[?(@.displayName == '%s')].id".formatted(label));
		return ids.getFirst();
	}

	private String webhook(String token, String chatId, String type, String username) {
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

	private String submit(String filename, String owner) throws Exception {
		String body = mockMvc.perform(multipart("/api/v1/analyses")
					.file(excel(filename)).param("mode", "LLM").with(user(owner)))
				.andReturn().getResponse().getContentAsString();
		return JsonPath.read(body, "$.analysisId");
	}
}
