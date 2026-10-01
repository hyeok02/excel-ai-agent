package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.verify;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.util.UUID;
import java.util.stream.IntStream;

import com.hyeok02.excelaiagent.email.domain.EmailRecipientRepository;
import com.hyeok02.excelaiagent.email.error.EmailDeliveryException;
import com.hyeok02.excelaiagent.email.error.EmailNotConfiguredException;
import com.hyeok02.excelaiagent.email.integration.EmailClient;
import com.hyeok02.excelaiagent.sharing.application.AnalysisPublicShareService;
import com.hyeok02.excelaiagent.sharing.application.IssuedAnalysisPublicShare;
import com.hyeok02.excelaiagent.sharing.domain.AnalysisPublicShare;
import com.hyeok02.excelaiagent.sharing.domain.AnalysisPublicShareRepository;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

class EmailShareControllerTests extends EmailRecipientTestSupport {
	@Test
	void sharesToSelectedRecipientsAndReportsPartialFailure() throws Exception {
		String firstId = register("alice", "first@example.com", "첫 번째");
		String secondId = register("alice", "second@example.com", "두 번째");
		String analysisId = submit("email-sales.xlsx", "alice");
		doThrow(new EmailDeliveryException()).when(emailClient)
				.send(eq("second@example.com"), anyString(), anyString(), anyString());

		mockMvc.perform(post("/api/v1/analyses/{id}/shares/email", analysisId)
					.with(user("alice"))
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"recipientIds\":[\"%s\",\"%s\"]}"
							.formatted(firstId, secondId)))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.requestedCount").value(2))
				.andExpect(jsonPath("$.successCount").value(1))
				.andExpect(jsonPath("$.failureCount").value(1))
				.andExpect(jsonPath("$.deliveries[0].success").value(true))
				.andExpect(jsonPath("$.deliveries[1].success").value(false))
				.andExpect(jsonPath("$.deliveries[1].errorMessage")
						.value("이메일을 전송하지 못했습니다."));

		List<AnalysisPublicShare> shares = publicShareRepository.findAll();
		assertThat(shares).hasSize(2);
		assertThat(shares).filteredOn(share -> share.getRevokedAt() == null)
				.singleElement().extracting(AnalysisPublicShare::getEmailRecipientId)
				.isEqualTo(UUID.fromString(firstId));
		assertThat(shares).filteredOn(share -> share.getRevokedAt() != null)
				.singleElement().extracting(AnalysisPublicShare::getEmailRecipientId)
				.isEqualTo(UUID.fromString(secondId));

		ArgumentCaptor<String> subject = ArgumentCaptor.forClass(String.class);
		ArgumentCaptor<String> plainText = ArgumentCaptor.forClass(String.class);
		ArgumentCaptor<String> html = ArgumentCaptor.forClass(String.class);
		verify(emailClient).send(
				eq("first@example.com"),
				subject.capture(),
				plainText.capture(),
				html.capture());
		assertThat(subject.getValue()).contains("Excel AI Agent", "sales.xlsx");
		assertThat(plainText.getValue())
				.contains("/shared/analysis/")
				.doesNotContain("/excel-analysis?id=");
		assertThat(html.getValue())
				.contains("Excel AI Agent", "상세 분석 결과 보기", "/shared/analysis/")
				.doesNotContain("/excel-analysis?id=");
	}

	@Test
	void rejectsEmptyOversizedAndAnotherOwnersSelection() throws Exception {
		String recipientId = register("bob", "bob@example.com", "Bob");
		String analysisId = submit("selection.xlsx", "alice");

		mockMvc.perform(post("/api/v1/analyses/{id}/shares/email", analysisId)
					.with(user("alice"))
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"recipientIds\":[]}"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_EMAIL_REQUEST"));

		mockMvc.perform(post("/api/v1/analyses/{id}/shares/email", analysisId)
					.with(user("alice"))
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"recipientIds\":[\"%s\"]}".formatted(recipientId)))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("EMAIL_RECIPIENT_NOT_FOUND"));

		String ids = IntStream.range(0, 51)
				.mapToObj(index -> "\"" + UUID.randomUUID() + "\"")
				.collect(java.util.stream.Collectors.joining(","));
		mockMvc.perform(post("/api/v1/analyses/{id}/shares/email", analysisId)
					.with(user("alice"))
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"recipientIds\":[" + ids + "]}"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.message")
						.value("이메일 수신자는 한 번에 최대 50명까지 선택할 수 있습니다."));
	}

	@Test
	void revokesIssuedLinkWhenEmailIsNotConfigured() throws Exception {
		String recipientId = register("alice", "disabled@example.com", "설정 없음");
		String analysisId = submit("email-config.xlsx", "alice");
		doThrow(new EmailNotConfiguredException()).when(emailClient)
				.send(eq("disabled@example.com"), anyString(), anyString(), anyString());

		mockMvc.perform(post("/api/v1/analyses/{id}/shares/email", analysisId)
					.with(user("alice"))
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"recipientIds\":[\"%s\"]}".formatted(recipientId)))
				.andExpect(status().isServiceUnavailable())
				.andExpect(jsonPath("$.code").value("EMAIL_NOT_CONFIGURED"));

		assertThat(publicShareRepository.findAll()).singleElement()
				.extracting(AnalysisPublicShare::getRevokedAt).isNotNull();
	}
}
