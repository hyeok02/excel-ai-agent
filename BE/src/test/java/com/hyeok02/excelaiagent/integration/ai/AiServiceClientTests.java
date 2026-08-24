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

import com.hyeok02.excelaiagent.analysis.domain.AnalysisDepth;
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
						        {
						          "cell": "D2",
						          "formula": "=SUM(B2:C2)",
						          "references": ["B2:C2"],
						          "cached_value": 15,
						          "role": "calculation"
						        }
						      ],
						      "region_count": 1,
						      "regions": [
						        {
						          "start_cell": "A1",
						          "end_cell": "D3",
						          "cell_count": 12,
						          "title": "월별 매출",
						          "row_count": 3,
						          "column_count": 4,
						          "merged_ranges": ["A1:B1"],
						          "header_paths": [{"column": "D", "labels": ["월별 매출", "합계"]}],
						          "preview_rows": [[
						            {
						              "address": "A1",
						              "value": "상품",
						              "formula": null,
						              "cached_value": null,
						              "number_format": "General",
						              "bold": true,
							  "fill_color": "FFEEF4FF",
							  "horizontal_alignment": "center",
							  "merged": true,
							  "semantic": {
							    "role": "header",
							    "confidence": 0.86,
							    "reasons": [{
							      "code": "header_style",
							      "message": "굵은 글꼴과 배경색",
							      "evidence_cells": ["Sales!A1"]
							    }]
							  }
							}
						  ]],
						  "is_truncated": true,
						  "semantic": {
						    "role": "data",
						    "confidence": 0.91,
						    "reasons": [{
						      "code": "tabular_values",
						      "message": "헤더 아래 반복 데이터",
						      "evidence_cells": ["Sales!A1:D3"]
						    }]
						  }
						}
						      ],
						      "tables": [
						        {
						          "name": "SalesTable",
						          "display_name": "SalesTable",
						          "reference": "A1:D3",
						          "headers": ["상품", "1월", "2월", "합계"],
						          "row_count": 3,
						          "column_count": 4,
						          "preview_rows": [],
						          "is_truncated": false
						        }
						      ],
						      "charts": [
						        {
						          "title": "월별 매출",
						          "chart_type": "BarChart",
						          "anchor_cell": "F2",
						          "series_count": 1,
						          "series": [{
						            "title": "1월",
						            "categories_reference": "'Sales'!$A$2:$A$3",
						            "values_reference": "'Sales'!$B$2:$B$3",
						            "category_samples": ["노트북", "모니터"],
						            "value_samples": [10, 5]
						          }],
						          "is_truncated": false
						        }
						      ]
						    }
						  ],
						  "dependency_summary": {
						    "node_count": 2,
						    "edge_count": 1,
						    "formula_node_count": 1,
						    "cross_sheet_edge_count": 0,
						    "named_reference_count": 0,
						    "external_reference_count": 0,
						    "cluster_count": 1,
						    "clusters": [{
						      "id": "cluster-1",
						      "node_count": 2,
						      "edge_count": 1,
						      "formula_count": 1,
						      "sheet_names": ["Sales"],
						      "nodes": [
						        {"id": "Sales!B2:C2", "label": "Sales!B2:C2", "sheet": "Sales", "cell": "B2:C2", "kind": "range", "formula": null},
						        {"id": "Sales!D2", "label": "Sales!D2", "sheet": "Sales", "cell": "D2", "kind": "formula", "formula": "=SUM(B2:C2)"}
						      ],
						      "edges": [{"source": "Sales!B2:C2", "target": "Sales!D2", "reference": "B2:C2", "cross_sheet": false}],
						      "is_truncated": false
						    }],
						    "cycle_count": 1,
						    "cyclic_node_count": 1,
						    "cycles": [{
						      "id": "cycle-1",
						      "node_count": 1,
						      "edge_count": 1,
						      "sheet_names": ["Sales"],
						      "nodes": [{"id": "Sales!D2", "label": "Sales!D2", "sheet": "Sales", "cell": "D2", "kind": "formula", "formula": "=D2+1"}],
						      "edges": [{"source": "Sales!D2", "target": "Sales!D2", "reference": "D2", "cross_sheet": false}],
						      "is_truncated": false
						    }]
						  }
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
		assertThat(response.dependencySummary().edgeCount()).isEqualTo(1);
		assertThat(response.dependencySummary().cycleCount()).isEqualTo(1);
		assertThat(response.dependencySummary().cycles()).singleElement().satisfies(cycle -> {
			assertThat(cycle.nodeCount()).isEqualTo(1);
			assertThat(cycle.nodes()).singleElement().satisfies(node ->
					assertThat(node.id()).isEqualTo("Sales!D2"));
		});
		assertThat(response.dependencySummary().clusters()).singleElement().satisfies(cluster -> {
			assertThat(cluster.sheetNames()).containsExactly("Sales");
			assertThat(cluster.edges()).singleElement().satisfies(edge -> {
				assertThat(edge.source()).isEqualTo("Sales!B2:C2");
				assertThat(edge.target()).isEqualTo("Sales!D2");
			});
		});
		assertThat(response.sheets()).singleElement().satisfies(sheet -> {
			assertThat(sheet.name()).isEqualTo("Sales");
			assertThat(sheet.formulaCount()).isEqualTo(1);
			assertThat(sheet.chartCount()).isEqualTo(1);
			assertThat(sheet.formulas()).singleElement().satisfies(formula -> {
				assertThat(formula.cell()).isEqualTo("D2");
				assertThat(formula.references()).containsExactly("B2:C2");
				assertThat(formula.cachedValue()).isEqualTo(15);
				assertThat(formula.role()).isEqualTo("calculation");
			});
			assertThat(sheet.regions()).singleElement().satisfies(region -> {
				assertThat(region.startCell()).isEqualTo("A1");
				assertThat(region.endCell()).isEqualTo("D3");
				assertThat(region.title()).isEqualTo("월별 매출");
				assertThat(region.rowCount()).isEqualTo(3);
				assertThat(region.columnCount()).isEqualTo(4);
				assertThat(region.mergedRanges()).containsExactly("A1:B1");
				assertThat(region.headerPaths()).singleElement().satisfies(header -> {
					assertThat(header.column()).isEqualTo("D");
					assertThat(header.labels()).containsExactly("월별 매출", "합계");
				});
				assertThat(region.previewRows().getFirst().getFirst()).satisfies(cell -> {
					assertThat(cell.value()).isEqualTo("상품");
					assertThat(cell.bold()).isTrue();
					assertThat(cell.fillColor()).isEqualTo("FFEEF4FF");
					assertThat(cell.horizontalAlignment()).isEqualTo("center");
					assertThat(cell.merged()).isTrue();
				});
				assertThat(region.truncated()).isTrue();
				assertThat(region.semantic().role()).isEqualTo(SemanticRole.DATA);
				assertThat(region.semantic().confidence()).isEqualTo(0.91);
				assertThat(region.semantic().reasons()).singleElement().satisfies(reason ->
						assertThat(reason.evidenceCells()).containsExactly("Sales!A1:D3"));
				assertThat(region.previewRows().getFirst().getFirst().semantic().role())
						.isEqualTo(SemanticRole.HEADER);
			});
			assertThat(sheet.tables()).singleElement().satisfies(table ->
					assertThat(table.reference()).isEqualTo("A1:D3"));
			assertThat(sheet.charts()).singleElement().satisfies(chart -> {
				assertThat(chart.title()).isEqualTo("월별 매출");
				assertThat(chart.anchorCell()).isEqualTo("F2");
				assertThat(chart.series()).singleElement().satisfies(series ->
						assertThat(series.valueSamples()).containsExactly(10, 5));
			});
		});
		server.verify();
	}

	@Test
	void sendsWorkbookAndReturnsGeneratedInsights() {
		server.expect(once(), requestTo("http://localhost:8000/api/v1/workbooks/insights"))
				.andExpect(method(POST))
				.andExpect(header("Content-Type", startsWith("multipart/form-data")))
				.andExpect(content().string(containsString("sales.xlsx")))
				.andExpect(content().string(containsString("PRECISE")))
				.andRespond(withSuccess(
						"""
						{
						  "workbook": {
						    "filename": "sales.xlsx",
						    "sheet_count": 1,
						    "sheets": []
						  },
						  "report": {
						    "overview": "수식이 포함된 단일 시트 워크북입니다.",
						    "insights": [
						      {
						        "title": "수식 검토 필요",
						        "description": "Sales 시트에 수식이 포함되어 있습니다.",
						        "category": "formula",
						        "severity": "warning",
						        "evidence": ["Sales!D2"],
						        "recommendation": "참조 범위를 확인하세요."
						      }
						    ],
						    "limitations": ["실제 셀 값은 분석하지 않았습니다."]
						  }
						}
						""",
						MediaType.APPLICATION_JSON));

		MockMultipartFile file = new MockMultipartFile(
				"file",
				"sales.xlsx",
				MediaType.APPLICATION_OCTET_STREAM_VALUE,
				new byte[] {0x50, 0x4b, 0x03, 0x04});

		AiWorkbookInsights response = aiServiceClient.generateWorkbookInsights(
				file,
				AnalysisDepth.PRECISE);

		assertThat(response.workbook().filename()).isEqualTo("sales.xlsx");
		assertThat(response.report().overview()).contains("단일 시트");
		assertThat(response.report().insights()).singleElement().satisfies(insight -> {
			assertThat(insight.category()).isEqualTo("formula");
			assertThat(insight.severity()).isEqualTo("warning");
			assertThat(insight.evidence()).containsExactly("Sales!D2");
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

	@Test
	void throwsUnavailableExceptionWhenWorkbookInsightRequestFails() {
		server.expect(once(), requestTo("http://localhost:8000/api/v1/workbooks/insights"))
				.andExpect(method(POST))
				.andRespond(withServerError());
		MockMultipartFile file = new MockMultipartFile(
				"file",
				"sales.xlsx",
				MediaType.APPLICATION_OCTET_STREAM_VALUE,
				new byte[] {0x50, 0x4b, 0x03, 0x04});

		assertThatThrownBy(() -> aiServiceClient.generateWorkbookInsights(file, AnalysisDepth.AUTO))
				.isInstanceOf(AiServiceUnavailableException.class);
		server.verify();
	}
}
