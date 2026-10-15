package com.hyeok02.excelaiagent.integration.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.http.HttpMethod.POST;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import java.util.List;

class AiWorkbookQuestionClientTests extends AiServiceClientTestSupport {
	@Test
	void sendsQuestionAndWorkbookAndReturnsGroundedAnswer() {
		server.expect(once(), requestTo("http://localhost:8000/api/v1/workbooks/questions"))
				.andExpect(method(POST))
				.andExpect(header("Content-Type", startsWith("multipart/form-data")))
				.andExpect(content().string(containsString("sales.xlsx")))
				.andExpect(content().string(containsString("노트북의 1월 값")))
				.andExpect(content().string(not(containsString("name=\"context\""))))
				.andRespond(withSuccess(fixture("workbook-question.json"), MediaType.APPLICATION_JSON));

		AiWorkbookQuestion response = client.askWorkbook(
				workbook().getResource(), "노트북의 1월 값은 얼마야?", false);

		assertThat(response.status()).isEqualTo("answered");
		assertThat(response.resolvedQuestion()).isNull();
		assertThat(response.selectedTools()).containsExactly("search_workbook_data");
		assertThat(response.verification().level()).isEqualTo("source_checked");
		assertThat(response.verification().checks()).containsExactly("cited_cells", "numbers");
		assertThat(response.evidence()).singleElement().satisfies(evidence -> {
			assertThat(evidence.sheetName()).isEqualTo("매출현황");
			assertThat(evidence.reference()).isEqualTo("B2");
			assertThat(evidence.value()).isEqualTo(10);
			assertThat(evidence.numberFormat()).isEqualTo("#,##0");
		});
		server.verify();
	}

	@Test
	void forwardsBoundedContextAsJsonAndReadsResolvedQuestion() {
		var context = new WorkbookQuestionContext(
				List.of(new WorkbookQuestionContext.Turn("노트북의 1월 값은?", List.of("매출현황!B2"))),
				List.of(new WorkbookQuestionContext.Insight("월별 매출", "노트북", List.of("매출현황!A1:C3"))));
		server.expect(once(), requestTo("http://localhost:8000/api/v1/workbooks/questions"))
				.andExpect(method(POST))
				.andExpect(content().string(containsString("name=\"context\"")))
				.andExpect(content().string(containsString("\"turns\":[{\"question\":\"노트북의 1월 값은?\"")))
				.andExpect(content().string(containsString("\"evidence\":[\"매출현황!B2\"]")))
				.andExpect(content().string(containsString("\"insights\":[{\"title\":\"월별 매출\"")))
				.andExpect(content().string(containsString("name=\"include_hidden_sheets\"\r\n")))
				.andRespond(withSuccess(fixture("workbook-question.json").replaceFirst("\\{",
						"{\"resolved_question\":\"노트북의 2월 값은 얼마야?\","), MediaType.APPLICATION_JSON));

		AiWorkbookQuestion response = client.askWorkbook(workbook().getResource(), "그럼 2월은?", true, context);

		assertThat(response.resolvedQuestion()).isEqualTo("노트북의 2월 값은 얼마야?");
		server.verify();
	}

	@Test
	void oldAnswersDoNotGainARequestVerificationGuarantee() {
		AiWorkbookQuestion response = new AiWorkbookQuestion(
				"합계는?", "100", "answered", 1.0,
				java.util.List.of(), java.util.List.of(), java.util.List.of());

		assertThat(response.verification().level()).isEqualTo("unverified");
		assertThat(response.verification().checks()).isEmpty();
	}
}
