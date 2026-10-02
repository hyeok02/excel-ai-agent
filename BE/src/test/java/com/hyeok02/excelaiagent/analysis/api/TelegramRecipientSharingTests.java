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

class TelegramRecipientSharingTests extends TelegramRecipientTestSupport {
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
}
