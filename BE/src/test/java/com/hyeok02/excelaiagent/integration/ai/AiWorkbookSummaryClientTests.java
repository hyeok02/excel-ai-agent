package com.hyeok02.excelaiagent.integration.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.http.HttpMethod.POST;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

class AiWorkbookSummaryClientTests extends AiServiceClientTestSupport {
	@Test
	void sendsWorkbookAndReturnsSummary() {
		server.expect(once(), requestTo("http://localhost:8000/api/v1/workbooks/summary"))
				.andExpect(method(POST))
				.andExpect(header("Content-Type", startsWith("multipart/form-data")))
				.andExpect(content().string(containsString("sales.xlsx")))
				.andRespond(withSuccess(fixture("workbook-summary.json"), MediaType.APPLICATION_JSON));
		AiWorkbookSummary response = client.summarizeWorkbook(workbook());
		assertThat(response.filename()).isEqualTo("sales.xlsx");
		assertThat(response.excludedSheets()).singleElement().satisfies(sheet -> {
			assertThat(sheet.analysisInclusion().decision()).isEqualTo(AnalysisDecision.EXCLUDE);
			assertThat(sheet.sheetClassification().role()).isEqualTo(SheetRole.SYSTEM);
		});
		assertThat(response.dependencySummary().cycles()).singleElement().satisfies(cycle ->
				assertThat(cycle.nodes().getFirst().id()).isEqualTo("Sales!D2"));
		assertThat(response.sheets()).singleElement().satisfies(sheet -> {
			assertThat(sheet.sheetClassification().role()).isEqualTo(SheetRole.OUTPUT);
			assertThat(sheet.columnSchemas()).singleElement().satisfies(column -> {
				assertThat(column.standardField()).isEqualTo("revenue");
				assertThat(column.unitType()).isEqualTo("currency");
				assertThat(column.provenance().analyzer()).isEqualTo("column_schema_analyzer");
				assertThat(column.provenance().evidence().getFirst().reference()).isEqualTo("A1:D3");
			});
			assertThat(sheet.formulas().getFirst().cachedValue()).isEqualTo(15);
			assertThat(sheet.formulas().getFirst().provenance().method()).isEqualTo("rule_based");
			assertThat(sheet.formulas().getFirst().provenance().evidence().getFirst().formula())
					.isEqualTo("=SUM(B2:C2)");
			assertThat(sheet.regions().getFirst().semantic().role()).isEqualTo(SemanticRole.DATA);
			assertThat(sheet.regions().getFirst().previewRows().getFirst().getFirst().semantic().role())
					.isEqualTo(SemanticRole.HEADER);
			assertThat(sheet.charts().getFirst().series().getFirst().valueSamples())
					.containsExactly(10, 5);
		});
		server.verify();
	}

	@Test
	void throwsUnavailableExceptionWhenWorkbookSummaryRequestFails() {
		server.expect(once(), requestTo("http://localhost:8000/api/v1/workbooks/summary"))
				.andExpect(method(POST)).andRespond(withServerError());
		assertThatThrownBy(() -> client.summarizeWorkbook(workbook()))
				.isInstanceOf(AiServiceUnavailableException.class);
		server.verify();
	}
}
