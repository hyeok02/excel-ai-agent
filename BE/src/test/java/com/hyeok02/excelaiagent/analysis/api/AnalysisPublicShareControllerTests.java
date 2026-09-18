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
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipient;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientRepository;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

class AnalysisPublicShareControllerTests extends AnalysisControllerTestSupport {
	@Autowired AnalysisPublicShareService publicShareService;
	@Autowired AnalysisPublicShareRepository publicShareRepository;
	@Autowired TelegramRecipientRepository recipientRepository;

	@AfterEach
	void removeShares() {
		publicShareRepository.deleteAll();
		recipientRepository.deleteAll();
	}

	@Test
	void returnsReadOnlyResultForValidBearerToken() throws Exception {
		UUID analysisId = UUID.fromString(submit("shared.xlsx", "system"));
		TelegramRecipient recipient = recipient("system", "10001");
		IssuedAnalysisPublicShare issued = publicShareService.issue(
				analysisId, recipient.getRecipientId(), "system");

		mockMvc.perform(get("/api/v1/public/analysis-shares/{token}", issued.token()))
				.andExpect(status().isOk())
				.andExpect(header().string("Cache-Control", "no-store"))
				.andExpect(header().string("Referrer-Policy", "no-referrer"))
				.andExpect(header().string("X-Robots-Tag", "noindex, nofollow, noarchive"))
				.andExpect(jsonPath("$.workbook.filename").value("sales.xlsx"))
				.andExpect(jsonPath("$.createdAt").exists())
				.andExpect(jsonPath("$.expiresAt").exists())
				.andExpect(jsonPath("$.analysisId").doesNotExist())
				.andExpect(jsonPath("$.sourceAvailable").doesNotExist());

		assertThat(publicShareRepository.findByTokenHash(issued.token())).isEmpty();
		assertThat(publicShareRepository.findByTokenHash(hash(issued.token()))).isPresent();
	}

	@Test
	void returnsSameNotFoundResponseForUnknownMalformedAndRevokedTokens() throws Exception {
		UUID analysisId = UUID.fromString(submit("private.xlsx", "system"));
		TelegramRecipient recipient = recipient("system", "10002");
		IssuedAnalysisPublicShare issued = publicShareService.issue(
				analysisId, recipient.getRecipientId(), "system");
		publicShareService.revoke(issued.shareId());

		assertUnavailable("not-a-token");
		assertUnavailable("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
		assertUnavailable(issued.token());
	}

	@Test
	void rejectsExpiredSharesAndSharesForInactiveRecipients() throws Exception {
		UUID analysisId = UUID.fromString(submit("private.xlsx", "system"));
		TelegramRecipient recipient = recipient("system", "10003");
		String expiredToken = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
		Instant now = Instant.now();
		publicShareRepository.save(AnalysisPublicShare.issue(
				analysisId, recipient.getRecipientId(), hash(expiredToken),
				now.minusSeconds(120), now.minusSeconds(60)));

		assertUnavailable(expiredToken);

		IssuedAnalysisPublicShare active = publicShareService.issue(
				analysisId, recipient.getRecipientId(), "system");
		recipient.deactivate(Instant.now());
		recipientRepository.save(recipient);
		assertUnavailable(active.token());
	}

	@Test
	void deletingAnalysisPermanentlyInvalidatesAndRemovesItsShare() throws Exception {
		UUID analysisId = UUID.fromString(submit("delete.xlsx", "system"));
		TelegramRecipient recipient = recipient("system", "10004");
		IssuedAnalysisPublicShare issued = publicShareService.issue(
				analysisId, recipient.getRecipientId(), "system");

		mockMvc.perform(delete("/api/v1/analyses/{analysisId}", analysisId)
					.with(user("system")))
				.andExpect(status().isNoContent());

		assertThat(publicShareRepository.findById(issued.shareId())).isEmpty();
		assertUnavailable(issued.token());
	}

	private TelegramRecipient recipient(String owner, String chatId) {
		return recipientRepository.save(TelegramRecipient.connected(
				owner, chatId, chatId, null, "공유", "수신자", null, Instant.now()));
	}

	private void assertUnavailable(String token) throws Exception {
		mockMvc.perform(get("/api/v1/public/analysis-shares/{token}", token))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("ANALYSIS_SHARE_NOT_FOUND"))
				.andExpect(jsonPath("$.message").value("공유 링크를 사용할 수 없습니다."));
	}

	private String submit(String filename, String owner) throws Exception {
		String body = mockMvc.perform(org.springframework.test.web.servlet.request
				.MockMvcRequestBuilders.multipart("/api/v1/analyses")
				.file(excel(filename)).param("mode", "LLM")
				.with(org.springframework.security.test.web.servlet.request
						.SecurityMockMvcRequestPostProcessors.user(owner)))
				.andReturn().getResponse().getContentAsString();
		return JsonPath.read(body, "$.analysisId");
	}

	private String hash(String token) throws Exception {
		return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
				.digest(token.getBytes(StandardCharsets.UTF_8)));
	}
}
