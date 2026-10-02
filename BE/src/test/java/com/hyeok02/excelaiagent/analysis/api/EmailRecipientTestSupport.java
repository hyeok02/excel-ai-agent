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

/** 이메일 수신자 테스트가 함께 쓰는 준비와 보조 메서드. */
abstract class EmailRecipientTestSupport extends AnalysisControllerTestSupport {
	@MockitoBean EmailClient emailClient;

	@Autowired EmailRecipientRepository recipientRepository;

	@Autowired AnalysisPublicShareRepository publicShareRepository;

	@Autowired AnalysisPublicShareService publicShareService;

	@BeforeEach
	void prepareEmail() {
		publicShareRepository.deleteAll();
		recipientRepository.deleteAll();
		reset(emailClient);
	}

	protected String register(
			String owner, String email, String displayName) throws Exception {
		String body = mockMvc.perform(post("/api/v1/email/recipients")
					.with(user(owner))
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"email\":\"%s\",\"displayName\":\"%s\"}"
							.formatted(email, displayName)))
				.andExpect(status().isCreated())
				.andReturn().getResponse().getContentAsString();
		return JsonPath.read(body, "$.id");
	}

	protected String submit(String filename, String owner) throws Exception {
		String body = mockMvc.perform(multipart("/api/v1/analyses")
					.file(excel(filename)).param("mode", "LLM").with(user(owner)))
				.andReturn().getResponse().getContentAsString();
		return JsonPath.read(body, "$.analysisId");
	}
}
