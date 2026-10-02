package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;

import com.hyeok02.excelaiagent.integration.ai.AiWritebackManifest;
import com.hyeok02.excelaiagent.integration.ai.AiWritebackPackage;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;

/**
 * 수정본 위에 다시 수정하기.
 *
 * 늘 원본에서 다시 시작하면 앞선 수정이 빠진 사본이 나오므로, 두 번째 수정은
 * 첫 번째 결과 위에 올라타야 한다.
 */
class WorkbookWritebackChainControllerTests extends WorkbookWritebackTestSupport {
	private static final byte[] FIRST_RESULT = {10, 20, 30};

	@BeforeEach
	void stubProposal() {
		when(aiWritebackClient.propose(any(), anyString())).thenReturn(proposal(false));
		when(aiWritebackClient.apply(any(), any())).thenReturn(
				new AiWritebackPackage(FIRST_RESULT, manifest()));
	}

	@Test
	void secondProposalReadsTheFirstResultInsteadOfTheOriginalUpload() throws Exception {
		String analysisId = submitCompleted();
		String first = applied(analysisId);

		String second = propose(analysisId);

		assertThat(JsonPath.<String>read(second, "$.baseWritebackId")).isEqualTo(first);
		assertThat(lastProposedSource()).isEqualTo(FIRST_RESULT);
	}

	@Test
	void theFirstEditStartsFromTheOriginalUpload() throws Exception {
		String analysisId = submitCompleted();

		String body = propose(analysisId);

		assertThat(JsonPath.<String>read(body, "$.baseWritebackId")).isNull();
		assertThat(lastProposedSource()).isNotEqualTo(FIRST_RESULT);
	}

	@Test
	void applyingTheSecondEditStacksItOnTheFirstResult() throws Exception {
		String analysisId = submitCompleted();
		String first = applied(analysisId);

		String writebackId = JsonPath.read(propose(analysisId), "$.writebackId");
		mockMvc.perform(post("/api/v1/analyses/{id}/writebacks/{wid}/approve",
					analysisId, writebackId).contentType(MediaType.APPLICATION_JSON)
					.content("{\"confirmed\":true}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("APPLIED"))
				.andExpect(jsonPath("$.baseWritebackId").value(first));

		assertThat(lastAppliedSource()).isEqualTo(FIRST_RESULT);
	}

	private String propose(String analysisId) throws Exception {
		return mockMvc.perform(post("/api/v1/analyses/{id}/writebacks", analysisId)
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"instruction\":\"B2를 12로 수정해줘\"}"))
				.andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
	}

	/** 한 건을 제안하고 승인해 수정본을 하나 만든다. */
	private String applied(String analysisId) throws Exception {
		String writebackId = JsonPath.read(propose(analysisId), "$.writebackId");
		mockMvc.perform(post("/api/v1/analyses/{id}/writebacks/{wid}/approve",
					analysisId, writebackId).contentType(MediaType.APPLICATION_JSON)
					.content("{\"confirmed\":true}"))
				.andExpect(status().isOk());
		return writebackId;
	}

	private byte[] lastProposedSource() throws Exception {
		ArgumentCaptor<Resource> captor = ArgumentCaptor.forClass(Resource.class);
		verify(aiWritebackClient, org.mockito.Mockito.atLeastOnce())
				.propose(captor.capture(), anyString());
		return captor.getValue().getContentAsByteArray();
	}

	private byte[] lastAppliedSource() throws Exception {
		ArgumentCaptor<Resource> captor = ArgumentCaptor.forClass(Resource.class);
		verify(aiWritebackClient, org.mockito.Mockito.atLeastOnce())
				.apply(captor.capture(), any());
		return captor.getValue().getContentAsByteArray();
	}

	private AiWritebackManifest manifest() {
		return new AiWritebackManifest(
				List.of("매출현황!B2"),
				List.of(new AiWritebackManifest.Check("formulas", true, "수식 보존")), true);
	}
}
