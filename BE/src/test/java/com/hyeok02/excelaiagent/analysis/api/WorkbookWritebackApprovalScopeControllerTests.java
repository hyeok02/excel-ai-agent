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

import com.hyeok02.excelaiagent.integration.ai.AiWritebackProposal;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;

class WorkbookWritebackApprovalScopeControllerTests extends WorkbookWritebackTestSupport {

	@BeforeEach
	void stubProposal() {
		when(aiWritebackClient.propose(any(), anyString())).thenReturn(dependentProposal());
		when(aiWritebackClient.apply(any(), any())).thenReturn(packageResult());
	}

	@Test
	void appliesOnlyTheApprovedCells() throws Exception {
		approve("{\"confirmed\":true,\"approvedCells\":[\"매출현황!B2\"]}")
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("APPLIED"));

		assertThat(appliedReferences()).containsExactly("B2");
	}

	@Test
	void appliesEveryChangeWhenNoCellIsListed() throws Exception {
		approve("{\"confirmed\":true}")
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("APPLIED"));

		assertThat(appliedReferences()).containsExactly("B2", "C2");
	}

	@Test
	void ignoresCellLetterCase() throws Exception {
		approve("{\"confirmed\":true,\"approvedCells\":[\"매출현황!c2\"]}")
				.andExpect(status().isOk());

		assertThat(appliedReferences()).containsExactly("C2");
	}

	@Test
	void rejectsCellsThatAreNotInTheProposal() throws Exception {
		approve("{\"confirmed\":true,\"approvedCells\":[\"매출현황!Z9\"]}")
				.andExpect(status().isConflict());
	}

	@Test
	void rejectsCellsMissingTheSheetName() throws Exception {
		approve("{\"confirmed\":true,\"approvedCells\":[\"B2\"]}")
				.andExpect(status().isConflict());
	}

	private org.springframework.test.web.servlet.ResultActions approve(String body)
			throws Exception {
		String analysisId = submitCompleted();
		String response = mockMvc.perform(post("/api/v1/analyses/{id}/writebacks", analysisId)
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"instruction\":\"B2와 C2를 수정해줘\"}"))
				.andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
		String writebackId = JsonPath.read(response, "$.writebackId");
		return mockMvc.perform(post("/api/v1/analyses/{id}/writebacks/{wid}/approve",
					analysisId, writebackId).contentType(MediaType.APPLICATION_JSON)
					.content(body));
	}

	@SuppressWarnings("unchecked")
	private List<String> appliedReferences() {
		ArgumentCaptor<List<AiWritebackProposal.Change>> captor =
				ArgumentCaptor.forClass(List.class);
		verify(aiWritebackClient).apply(any(Resource.class), captor.capture());
		return captor.getValue().stream().map(AiWritebackProposal.Change::reference).toList();
	}
}
