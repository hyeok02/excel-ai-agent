package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.HexFormat;
import java.util.UUID;

import com.hyeok02.excelaiagent.sharing.application.AnalysisPublicShareService;
import com.hyeok02.excelaiagent.sharing.application.IssuedAnalysisPublicShare;
import com.hyeok02.excelaiagent.sharing.domain.AnalysisPublicShare;
import com.hyeok02.excelaiagent.sharing.domain.AnalysisPublicShareRepository;
import com.hyeok02.excelaiagent.email.domain.EmailRecipient;
import com.hyeok02.excelaiagent.email.domain.EmailRecipientRepository;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipient;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientRepository;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/** 공개 공유 링크 테스트가 함께 쓰는 준비와 보조 메서드. */
abstract class AnalysisPublicShareTestSupport extends AnalysisControllerTestSupport {
	@Autowired AnalysisPublicShareService publicShareService;

	@Autowired AnalysisPublicShareRepository publicShareRepository;

	@Autowired TelegramRecipientRepository recipientRepository;

	@Autowired EmailRecipientRepository emailRecipientRepository;

	@AfterEach
	void removeShares() {
		publicShareRepository.deleteAll();
		recipientRepository.deleteAll();
		emailRecipientRepository.deleteAll();
	}

	protected TelegramRecipient recipient(String owner, String chatId) {
		return recipientRepository.save(TelegramRecipient.connected(
				owner, chatId, chatId, null, "공유", "수신자", null, Instant.now()));
	}

	protected void assertUnavailable(String token) throws Exception {
		mockMvc.perform(get("/api/v1/public/analysis-shares/{token}", token))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("ANALYSIS_SHARE_NOT_FOUND"))
				.andExpect(jsonPath("$.message").value("공유 링크를 사용할 수 없습니다."));
	}

	protected String submit(String filename, String owner) throws Exception {
		String body = mockMvc.perform(org.springframework.test.web.servlet.request
				.MockMvcRequestBuilders.multipart("/api/v1/analyses")
				.file(excel(filename)).param("mode", "LLM")
				.with(org.springframework.security.test.web.servlet.request
						.SecurityMockMvcRequestPostProcessors.user(owner)))
				.andReturn().getResponse().getContentAsString();
		return JsonPath.read(body, "$.analysisId");
	}

	protected String hash(String token) throws Exception {
		return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
				.digest(token.getBytes(StandardCharsets.UTF_8)));
	}
}
