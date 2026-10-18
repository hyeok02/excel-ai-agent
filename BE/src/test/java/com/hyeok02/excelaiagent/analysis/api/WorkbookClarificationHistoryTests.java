package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import com.hyeok02.excelaiagent.analysis.domain.WorkbookQuestion;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookQuestion;
import com.hyeok02.excelaiagent.integration.ai.WorkbookQuestionContext;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;

class WorkbookClarificationHistoryTests extends WorkbookQuestionHistoryTestSupport {
	@Test
	void structuredChoicesSurviveStorageAndSelectedAnswerIsAddedWithoutReplacingOriginal() throws Exception {
		UUID analysisId = completed("system");
		String optionId = "b".repeat(64);
		var option = new AiWorkbookQuestion.ClarificationOption(optionId,
				"매출 (USD)", "실적!B1:B5", "통화 USD", "실적 시트 매출 (USD) 합계는?");
		var clarification = new AiWorkbookQuestion("매출 합계는?", "항목을 선택해 주세요.",
				"insufficient_evidence", 0, List.of("clarify_source_scope"), List.of(), List.of(),
				null, null, List.of(option));
		historyService.save(analysisId, "system", clarification.question(), clarification);
		assertThat(history(analysisId, null, null).get("items").get(0).get("answer"))
				.isEqualTo(objectMapper.valueToTree(clarification));

		var selected = answer(option.question(), "limited");
		when(aiServiceClient.askWorkbook(any(Resource.class), any(), anyBoolean(), any())).thenReturn(selected);
		String request = """
				{"question":"실적 시트 매출 (USD) 합계는?","context":{"selection":{
				 "source_question":"매출 합계는?","option_id":"%s","answer":"untrusted"}}}
				""".formatted(optionId);
		mockMvc.perform(post("/api/v1/analyses/{id}/questions", analysisId)
				.contentType(MediaType.APPLICATION_JSON).content(request)).andExpect(status().isOk());
		var context = ArgumentCaptor.forClass(WorkbookQuestionContext.class);
		verify(aiServiceClient).askWorkbook(any(Resource.class), any(), anyBoolean(), context.capture());
		assertThat(context.getValue().selection()).isEqualTo(
				new WorkbookQuestionContext.Selection(clarification.question(), optionId));
		assertThat(objectMapper.writeValueAsString(context.getValue())).doesNotContain("untrusted", "answer");
		var items = history(analysisId, null, null).get("items");
		assertThat(items.size()).isEqualTo(2);
		assertThat(items.get(0).get("answer")).isEqualTo(objectMapper.valueToTree(clarification));
		assertThat(items.get(1).get("answer")).isEqualTo(objectMapper.valueToTree(selected));
	}

	@Test
	void oldPersistedAnswersWithoutOptionsRestoreAsEmptyChoices() throws Exception {
		UUID id = completed("system");
		var old = objectMapper.valueToTree(answer("기존 질문", "limited")).deepCopy();
		((tools.jackson.databind.node.ObjectNode) old).remove("clarificationOptions");
		questionRepository.saveAndFlush(WorkbookQuestion.answered(id, "기존 질문", old.toString(), Instant.now()));
		assertThat(history(id, null, null).get("items").get(0).get("answer").get("clarificationOptions").size())
				.isZero();
	}
}
