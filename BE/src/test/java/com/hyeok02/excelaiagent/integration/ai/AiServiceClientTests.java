package com.hyeok02.excelaiagent.integration.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.http.HttpMethod.GET;
import static org.springframework.http.HttpMethod.POST;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.startsWith;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class AiServiceClientTests {

	private MockRestServiceServer server;
	private AiServiceClient aiServiceClient;

	@BeforeEach
	void setUp() {
		RestClient.Builder builder = RestClient.builder().baseUrl("http://localhost:8000");
		server = MockRestServiceServer.bindTo(builder).build();
		aiServiceClient = new AiServiceClient(builder.build());
	}

	@Test
	void returnsFastApiHealthResponse() {
		server.expect(once(), requestTo("http://localhost:8000/health"))
				.andExpect(method(GET))
				.andRespond(withSuccess(
						"{\"status\":\"UP\",\"service\":\"excel-ai-agent-service\"}",
						MediaType.APPLICATION_JSON));

		AiServiceClient.AiServiceHealth response = aiServiceClient.checkHealth();

		assertThat(response.status()).isEqualTo("UP");
		assertThat(response.service()).isEqualTo("excel-ai-agent-service");
		server.verify();
	}

	@Test
	void throwsUnavailableExceptionWhenFastApiReturnsError() {
		server.expect(once(), requestTo("http://localhost:8000/health"))
				.andExpect(method(GET))
				.andRespond(withServerError());

		assertThatThrownBy(aiServiceClient::checkHealth)
				.isInstanceOf(AiServiceUnavailableException.class);
		server.verify();
	}

	@Test
	void sendsWorkbookAndReturnsSummary() {
		server.expect(once(), requestTo("http://localhost:8000/api/v1/workbooks/summary"))
				.andExpect(method(POST))
				.andExpect(header("Content-Type", startsWith("multipart/form-data")))
				.andExpect(content().string(containsString("sales.xlsx")))
				.andRespond(withSuccess(
						"""
						{
						  "filename": "sales.xlsx",
						  "sheet_count": 1,
						  "sheets": [
						    {
						      "name": "Sales",
						      "rows": 3,
						      "columns": 4,
						      "formula_count": 1,
						      "table_count": 0,
						      "chart_count": 1,
						      "formulas": [
						        {"cell": "D2", "formula": "=SUM(B2:C2)", "references": ["B2:C2"]}
						      ],
						      "region_count": 1,
						      "regions": [
						        {"start_cell": "A1", "end_cell": "D3", "cell_count": 12}
						      ]
						    }
						  ]
						}
						""",
						MediaType.APPLICATION_JSON));

		MockMultipartFile file = new MockMultipartFile(
				"file",
				"sales.xlsx",
				"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				new byte[] {0x50, 0x4b, 0x03, 0x04});

		AiWorkbookSummary response = aiServiceClient.summarizeWorkbook(file);

		assertThat(response.filename()).isEqualTo("sales.xlsx");
		assertThat(response.sheetCount()).isEqualTo(1);
		assertThat(response.sheets()).singleElement().satisfies(sheet -> {
			assertThat(sheet.name()).isEqualTo("Sales");
			assertThat(sheet.formulaCount()).isEqualTo(1);
			assertThat(sheet.chartCount()).isEqualTo(1);
			assertThat(sheet.formulas()).singleElement().satisfies(formula -> {
				assertThat(formula.cell()).isEqualTo("D2");
				assertThat(formula.references()).containsExactly("B2:C2");
			});
			assertThat(sheet.regions()).singleElement().satisfies(region -> {
				assertThat(region.startCell()).isEqualTo("A1");
				assertThat(region.endCell()).isEqualTo("D3");
			});
		});
		server.verify();
	}

	@Test
	void throwsUnavailableExceptionWhenWorkbookSummaryRequestFails() {
		server.expect(once(), requestTo("http://localhost:8000/api/v1/workbooks/summary"))
				.andExpect(method(POST))
				.andRespond(withServerError());
		MockMultipartFile file = new MockMultipartFile(
				"file",
				"sales.xlsx",
				MediaType.APPLICATION_OCTET_STREAM_VALUE,
				new byte[] {0x50, 0x4b, 0x03, 0x04});

		assertThatThrownBy(() -> aiServiceClient.summarizeWorkbook(file))
				.isInstanceOf(AiServiceUnavailableException.class);
		server.verify();
	}
}
