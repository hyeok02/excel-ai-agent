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

class EmailRecipientControllerTests extends EmailRecipientTestSupport {
	@Test
	void registersNormalizedRecipientAndScopesItToOwner() throws Exception {
		mockMvc.perform(post("/api/v1/email/recipients")
					.with(user("alice"))
					.contentType(MediaType.APPLICATION_JSON)
					.content("""
							{"email":"Finance@Example.COM","displayName":" 재무팀 김대리 "}
							"""))
				.andExpect(status().isCreated())
				.andExpect(jsonPath("$.displayName").value("재무팀 김대리"))
				.andExpect(jsonPath("$.email").value("finance@example.com"))
				.andExpect(jsonPath("$.status").value("ACTIVE"));

		mockMvc.perform(get("/api/v1/email/recipients").with(user("alice")))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$[0].email").value("finance@example.com"));
		mockMvc.perform(get("/api/v1/email/recipients").with(user("bob")))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$").isEmpty());

		mockMvc.perform(post("/api/v1/email/recipients")
					.with(user("alice"))
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"email\":\"FINANCE@example.com\"}"))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("DUPLICATE_EMAIL_RECIPIENT"));

		mockMvc.perform(post("/api/v1/email/recipients")
					.with(user("alice"))
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"email\":\"not-an-email\"}"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("VALIDATION_ERROR"))
				.andExpect(jsonPath("$.fieldErrors.email").exists());
	}

	@Test
	void deactivatesOwnedRecipientRevokesLinksAndAllowsReAdd() throws Exception {
		String recipientId = register("alice", "old@example.com", "이전 이름");
		UUID analysisId = UUID.fromString(submit("deactivate-email.xlsx", "alice"));
		IssuedAnalysisPublicShare share = publicShareService.issueForEmail(
				analysisId, UUID.fromString(recipientId), "alice");

		mockMvc.perform(delete("/api/v1/email/recipients/{id}", recipientId)
					.with(user("bob")))
				.andExpect(status().isNotFound());
		mockMvc.perform(delete("/api/v1/email/recipients/{id}", recipientId)
					.with(user("alice")))
				.andExpect(status().isNoContent());

		assertThat(publicShareRepository.findById(share.shareId()))
				.get().extracting(AnalysisPublicShare::getRevokedAt).isNotNull();
		mockMvc.perform(get("/api/v1/email/recipients").with(user("alice")))
				.andExpect(jsonPath("$").isEmpty());

		String readdedId = register("alice", "OLD@example.com", "새 이름");
		assertThat(readdedId).isEqualTo(recipientId);
		mockMvc.perform(get("/api/v1/email/recipients").with(user("alice")))
				.andExpect(jsonPath("$[0].displayName").value("새 이름"));
	}
}
