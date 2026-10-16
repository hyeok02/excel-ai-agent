package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import tools.jackson.databind.JsonNode;

class WorkbookQuestionHistoryPaginationTests extends WorkbookQuestionHistoryTestSupport {
	@Test
	void paginatesOldestFirstWithinPageWithExclusiveStableCursor() throws Exception {
		UUID id = completed("system");
		for (int index = 1; index <= 5; index++) {
			historyService.save(id, "system", "q" + index, answer("q" + index, "answered"));
		}
		JsonNode first = history(id, null, "2");
		assertQuestions(first, "q4", "q5");
		String cursor = first.get("nextCursor").asString();
		assertThat(cursor).isEqualTo(first.get("items").get(0).get("id").asString());

		// A new completed answer does not shift older pages or duplicate an already displayed turn.
		historyService.save(id, "system", "q6", answer("q6", "answered"));
		JsonNode second = history(id, cursor, "2");
		assertQuestions(second, "q2", "q3");
		JsonNode third = history(id, second.get("nextCursor").asString(), "2");
		assertQuestions(third, "q1");
		assertThat(third.get("nextCursor").isNull()).isTrue();
		assertThat(history(id, "1", "2").get("items").size()).isZero();
	}

	@Test
	void defaultsToThirtyAndDoesNotInventCursorForExactPage() throws Exception {
		UUID id = completed("system");
		for (int index = 1; index <= 31; index++) {
			historyService.save(id, "system", "q" + index, answer("q" + index, "answered"));
		}
		JsonNode page = history(id, null, null);
		assertThat(page.get("items").size()).isEqualTo(30);
		assertThat(page.get("nextCursor").isString()).isTrue();
		assertThat(history(id, null, "31").get("nextCursor").isNull()).isTrue();
	}

	@ParameterizedTest
	@CsvSource({"before,0", "before,-1", "before,abc", "before,9223372036854775808",
			"size,0", "size,-1", "size,101", "size,abc"})
	void rejectsInvalidPagination(String parameter, String value) throws Exception {
		mockMvc.perform(get("/api/v1/analyses/{id}/questions", UUID.randomUUID()).param(parameter, value))
				.andExpect(status().isBadRequest());
	}
}
