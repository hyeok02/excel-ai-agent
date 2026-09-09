package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hyeok02.excelaiagent.telegram.error.TelegramDeliveryException;
import com.hyeok02.excelaiagent.telegram.integration.TelegramClient;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

class TelegramShareControllerTests extends AnalysisControllerTestSupport {
	@MockitoBean TelegramClient telegramClient;

	@Test
	void sendsOwnedAnalysisSummaryToConfiguredTelegramChat() throws Exception {
		String id = submit("sales.xlsx", "system");

		mockMvc.perform(post("/api/v1/analyses/{analysisId}/shares/telegram", id))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.sentAt").exists());

		ArgumentCaptor<String> message = ArgumentCaptor.forClass(String.class);
		verify(telegramClient).sendMessage(message.capture());
		assertThat(message.getValue())
				.contains("📊 Excel 분석 완료", "sales.xlsx", "수식 참조 확인")
				.contains("/excel-analysis?id=" + id);
	}

	@Test
	void hidesAnotherUsersAnalysisFromTelegramShare() throws Exception {
		String id = submit("private.xlsx", "alice");

		mockMvc.perform(post("/api/v1/analyses/{analysisId}/shares/telegram", id)
					.with(user("bob")))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("ANALYSIS_NOT_FOUND"));
		verifyNoInteractions(telegramClient);
	}

	@Test
	void returnsSanitizedErrorWhenTelegramRejectsDelivery() throws Exception {
		String id = submit("sales.xlsx", "system");
		doThrow(new TelegramDeliveryException()).when(telegramClient).sendMessage(
				org.mockito.ArgumentMatchers.anyString());

		mockMvc.perform(post("/api/v1/analyses/{analysisId}/shares/telegram", id))
				.andExpect(status().isBadGateway())
				.andExpect(jsonPath("$.code").value("TELEGRAM_DELIVERY_FAILED"))
				.andExpect(jsonPath("$.message")
						.value("텔레그램 메시지를 전송하지 못했습니다."));
	}

	private String submit(String filename, String owner) throws Exception {
		String body = mockMvc.perform(multipart("/api/v1/analyses")
					.file(excel(filename)).param("mode", "LLM").with(user(owner)))
				.andReturn().getResponse().getContentAsString();
		return JsonPath.read(body, "$.analysisId");
	}
}
