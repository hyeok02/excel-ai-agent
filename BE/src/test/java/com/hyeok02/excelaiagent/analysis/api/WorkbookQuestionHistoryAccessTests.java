package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.error.AnalysisNotFoundException;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;

class WorkbookQuestionHistoryAccessTests extends WorkbookQuestionHistoryTestSupport {
	@Test
	void isolatesFilesAndOwnersForReadsAndWrites() throws Exception {
		UUID aliceFirst = completed("alice");
		UUID aliceSecond = completed("alice");
		UUID bob = completed("bob");
		historyService.save(aliceFirst, "alice", "first", answer("first", "limited"));
		historyService.save(aliceSecond, "alice", "second", answer("second", "answered"));
		historyService.save(bob, "bob", "private", answer("private", "answered"));

		mockMvc.perform(get("/api/v1/analyses/{id}/questions", aliceFirst).with(user("alice")))
				.andExpect(status().isOk()).andExpect(jsonPath("$.items.length()").value(1))
				.andExpect(jsonPath("$.items[0].answer.question").value("first"));
		mockMvc.perform(get("/api/v1/analyses/{id}/questions", bob).with(user("alice")))
				.andExpect(status().isNotFound());
		mockMvc.perform(post("/api/v1/analyses/{id}/questions", bob).with(user("alice"))
				.contentType(MediaType.APPLICATION_JSON).content("{\"question\":\"private\"}"))
				.andExpect(status().isNotFound());
		assertThatThrownBy(() -> historyService.save(bob, "alice", "private", answer("private", "answered")))
				.isInstanceOf(AnalysisNotFoundException.class);
		assertThat(questionRepository.count()).isEqualTo(3);
		verify(aiServiceClient, never()).askWorkbook(any(Resource.class), any(), anyBoolean());
	}

	@Test
	void readsSavedAnswersAfterSourceExpiresButRejectsNewQuestion() throws Exception {
		UUID id = completed("system");
		historyService.save(id, "system", "original", answer("original", "limited"));
		analysisFileStorage.delete(id);

		mockMvc.perform(get("/api/v1/analyses/{id}/questions", id))
				.andExpect(status().isOk()).andExpect(jsonPath("$.items[0].answer.status").value("limited"));
		mockMvc.perform(post("/api/v1/analyses/{id}/questions", id)
				.contentType(MediaType.APPLICATION_JSON).content("{\"question\":\"또 질문\"}"))
				.andExpect(status().isGone());
		assertThat(questionRepository.count()).isEqualTo(1);
		verify(aiServiceClient, never()).askWorkbook(any(Resource.class), any(), anyBoolean());
	}

	@Test
	void deletesQuestionHistoryWithItsAnalysis() throws Exception {
		UUID id = completed("system");
		UUID other = completed("system");
		historyService.save(id, "system", "delete", answer("delete", "answered"));
		historyService.save(other, "system", "keep", answer("keep", "answered"));
		mockMvc.perform(delete("/api/v1/analyses/{id}", id)).andExpect(status().isNoContent());
		assertThat(questionRepository.count()).isEqualTo(1);
		assertQuestions(history(other, null, null), "keep");
		mockMvc.perform(get("/api/v1/analyses/{id}/questions", id)).andExpect(status().isNotFound());
	}
}
