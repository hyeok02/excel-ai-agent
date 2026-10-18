package com.hyeok02.excelaiagent.integration.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import tools.jackson.databind.json.JsonMapper;

class AiQuestionClarificationTests extends AiServiceClientTestSupport {

	@Test
	void forwardsSelectionWithSnakeCaseAndReadsStructuredOptions() {
		String id = "a".repeat(64);
		var context = new WorkbookQuestionContext(List.of(), List.of(),
				new WorkbookQuestionContext.Selection("매출 합계는?", id));
		String json = """
				{"question":"매출 합계는?","answer":"항목을 선택해 주세요.",
				 "status":"insufficient_evidence","confidence":0,"selected_tools":[],
				 "evidence":[],"limitations":[],"clarification_options":[{
				 "id":"%s","label":"매출 (USD)","scope":"실적!B1:B5",
				 "details":"통화 USD","question":"실적 시트의 매출 (USD) 합계는?"}]}
				""".formatted(id);
		server.expect(requestTo("http://localhost:8000/api/v1/workbooks/questions"))
				.andExpect(content().string(containsString("\"source_question\":\"매출 합계는?\"")))
				.andExpect(content().string(containsString("\"option_id\":\"" + id + "\"")))
				.andRespond(withSuccess(json, MediaType.APPLICATION_JSON));
		var result = client.askWorkbook(workbook().getResource(), "매출 (USD) 합계는?", false, context);
		assertThat(result.clarificationOptions()).singleElement().satisfies(option -> {
			assertThat(option.id()).isEqualTo(id);
			assertThat(option.question()).isEqualTo("실적 시트의 매출 (USD) 합계는?");
		});
		String response = JsonMapper.builder().build().writeValueAsString(result);
		assertThat(response).contains("\"clarificationOptions\"").doesNotContain("clarification_options");
		server.verify();
	}

	@Test
	void oldAnswersAndContextsRemainReadableWithoutActions() {
		var mapper = JsonMapper.builder().build();
		var answer = mapper.readValue(fixture("workbook-question.json"), AiWorkbookQuestion.class);
		assertThat(answer.clarificationOptions()).isEmpty();
		assertThat(mapper.readValue("{}", WorkbookQuestionContext.class).selection()).isNull();
		assertThat(new WorkbookQuestionContext(List.of(), List.of()).selection()).isNull();
	}
}
