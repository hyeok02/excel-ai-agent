package com.hyeok02.excelaiagent.analysis.api;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.UUID;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

class WorkbookWritebackControllerTests extends WorkbookWritebackTestSupport {
	@Test
	void createsProposalOnlyThenAppliesVerifiedCopyAfterExplicitApproval() throws Exception {
		when(aiWritebackClient.propose(any(), anyString())).thenReturn(proposal(false));
		when(aiWritebackClient.apply(any(), any())).thenReturn(packageResult());
		String analysisId = submitCompleted();
		String response = mockMvc.perform(post("/api/v1/analyses/{id}/writebacks", analysisId)
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"instruction\":\"B2를 12로 수정해줘\"}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("PROPOSED"))
				.andExpect(jsonPath("$.downloadable").value(false))
				.andReturn().getResponse().getContentAsString();
		String writebackId = JsonPath.read(response, "$.writebackId");

		mockMvc.perform(post("/api/v1/analyses/{id}/writebacks/{wid}/approve",
					analysisId, writebackId).contentType(MediaType.APPLICATION_JSON)
					.content("{\"confirmed\":false}"))
				.andExpect(status().isConflict());
		mockMvc.perform(post("/api/v1/analyses/{id}/writebacks/{wid}/approve",
					analysisId, writebackId).contentType(MediaType.APPLICATION_JSON)
					.content("{\"confirmed\":true}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("APPLIED"))
				.andExpect(jsonPath("$.verification.verified").value(true));
		mockMvc.perform(get("/api/v1/analyses/{id}/writebacks/{wid}/download",
					analysisId, writebackId))
				.andExpect(status().isOk()).andExpect(content().bytes(new byte[] {1, 2, 3}));
	}

	@Test
	void storesBlockedProposalWithoutApprovalAction() throws Exception {
		when(aiWritebackClient.propose(any(), anyString())).thenReturn(proposal(true));
		String analysisId = submitCompleted();
		String response = mockMvc.perform(post("/api/v1/analyses/{id}/writebacks", analysisId)
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"instruction\":\"수식을 바꿔줘\"}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("BLOCKED"))
				.andReturn().getResponse().getContentAsString();
		String writebackId = JsonPath.read(response, "$.writebackId");
		mockMvc.perform(post("/api/v1/analyses/{id}/writebacks/{wid}/approve",
					analysisId, writebackId).contentType(MediaType.APPLICATION_JSON)
					.content("{\"confirmed\":true}"))
				.andExpect(status().isConflict());
	}

	@Test
	void returnsGoneForNewWritebackWhenTheOriginalFileHasExpired() throws Exception {
		String analysisId = submitCompleted();
		analysisFileStorage.delete(UUID.fromString(analysisId));

		mockMvc.perform(post("/api/v1/analyses/{id}/writebacks", analysisId)
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"instruction\":\"B2를 12로 수정해줘\"}"))
				.andExpect(status().isGone())
				.andExpect(jsonPath("$.code").value("ANALYSIS_SOURCE_UNAVAILABLE"));

		mockMvc.perform(get("/api/v1/analyses/{id}/writebacks", analysisId))
				.andExpect(status().isOk());
	}

	@Test
	void hidesAnotherUsersWritebackHistory() throws Exception {
		String analysisId = submitCompleted("alice");

		mockMvc.perform(get("/api/v1/analyses/{id}/writebacks", analysisId)
					.with(user("bob")))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("ANALYSIS_NOT_FOUND"));
	}

}
