package com.hyeok02.excelaiagent.integration.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.http.HttpMethod.POST;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

class AiWorkbookQuestionClientTests extends AiServiceClientTestSupport {
	@Test
	void sendsQuestionAndWorkbookAndReturnsGroundedAnswer() {
		server.expect(once(), requestTo("http://localhost:8000/api/v1/workbooks/questions"))
				.andExpect(method(POST))
				.andExpect(header("Content-Type", startsWith("multipart/form-data")))
				.andExpect(content().string(containsString("sales.xlsx")))
				.andExpect(content().string(containsString("노트북의 1월 값")))
				.andRespond(withSuccess(fixture("workbook-question.json"), MediaType.APPLICATION_JSON));

		AiWorkbookQuestion response = client.askWorkbook(
				workbook().getResource(), "노트북의 1월 값은 얼마야?");

		assertThat(response.status()).isEqualTo("answered");
		assertThat(response.selectedTools()).containsExactly("search_workbook_data");
		assertThat(response.evidence()).singleElement().satisfies(evidence -> {
			assertThat(evidence.sheetName()).isEqualTo("매출현황");
			assertThat(evidence.reference()).isEqualTo("B2");
			assertThat(evidence.value()).isEqualTo(10);
		});
		server.verify();
	}
}
