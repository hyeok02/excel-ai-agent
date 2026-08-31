package com.hyeok02.excelaiagent.integration.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.http.HttpMethod.POST;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisDepth;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

class AiWorkbookInsightClientTests extends AiServiceClientTestSupport {
	@Test
	void sendsWorkbookAndReturnsGeneratedInsights() {
		server.expect(once(), requestTo("http://localhost:8000/api/v1/workbooks/insights"))
				.andExpect(method(POST))
				.andExpect(content().string(containsString("sales.xlsx")))
				.andExpect(content().string(containsString("PRECISE")))
				.andRespond(withSuccess(fixture("workbook-insights.json"), MediaType.APPLICATION_JSON));
		AiWorkbookInsights response = client.generateWorkbookInsights(workbook(), AnalysisDepth.PRECISE);
		assertThat(response.workbook().filename()).isEqualTo("sales.xlsx");
		assertThat(response.report().insights()).singleElement().satisfies(insight -> {
			assertThat(insight.category()).isEqualTo("formula");
			assertThat(insight.fact()).contains("Sales 시트");
			assertThat(insight.confidence()).isEqualTo(0.95);
			assertThat(insight.validationStatus()).isEqualTo("verified");
			assertThat(response.report().validation().verifiedCount()).isEqualTo(1);
			assertThat(insight.evidence()).containsExactly("Sales!D2");
		});
		server.verify();
	}

	@Test
	void throwsUnavailableExceptionWhenWorkbookInsightRequestFails() {
		server.expect(once(), requestTo("http://localhost:8000/api/v1/workbooks/insights"))
				.andExpect(method(POST)).andRespond(withServerError());
		assertThatThrownBy(() -> client.generateWorkbookInsights(workbook(), AnalysisDepth.AUTO))
				.isInstanceOf(AiServiceUnavailableException.class);
		server.verify();
	}
}
