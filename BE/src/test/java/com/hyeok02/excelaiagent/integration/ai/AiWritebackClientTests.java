package com.hyeok02.excelaiagent.integration.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.http.HttpMethod.POST;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;
import tools.jackson.databind.json.JsonMapper;

class AiWritebackClientTests {
	private MockRestServiceServer server;
	private AiWritebackClient client;
	private JsonMapper jsonMapper;

	@BeforeEach
	void setUp() {
		RestClient.Builder builder = RestClient.builder().baseUrl("http://localhost:8000");
		server = MockRestServiceServer.bindTo(builder).build();
		jsonMapper = JsonMapper.builder().build();
		client = new AiWritebackClient(builder.build(), jsonMapper);
	}

	@Test
	void serializesApprovedChangesWithPythonFieldNamesAndReadsVerifiedArchive() {
		server.expect(requestTo("http://localhost:8000/api/v1/workbooks/writebacks/apply"))
				.andExpect(method(POST))
				.andExpect(content().string(containsString("sheet_name")))
				.andExpect(content().string(containsString("old_value")))
				.andExpect(content().string(containsString("value_type")))
				.andRespond(withSuccess(archive(), MediaType.APPLICATION_OCTET_STREAM));
		AiWritebackProposal.Change change = new AiWritebackProposal.Change(
				"매출현황", "B2", 12, "정정", 10, List.of(),
				"value", "number", List.of("매출현황!D2"), "medium");

		AiWritebackPackage result = client.apply(workbook().getResource(), List.of(change));

		assertThat(result.workbook()).containsExactly(1, 2, 3);
		assertThat(result.manifest().verified()).isTrue();
		assertThat(result.manifest().changedCells()).containsExactly("매출현황!B2");
		server.verify();
	}

	@Test
	void readsSnakeCaseProposalFromPythonService() {
		String response = """
				{"instruction":"B2 수정","status":"ready","summary":"변경 제안",
				"changes":[{"sheet_name":"매출현황","reference":"B2","old_value":10,
				"new_value":12,"reason":"정정","context_cells":[{"reference":"A2",
				"value":"노트북"}]}],"risks":[],"limitations":[]}
				""";
		server.expect(requestTo("http://localhost:8000/api/v1/workbooks/writeback-proposals"))
				.andExpect(method(POST))
				.andExpect(content().string(containsString("B2를 12로 수정")))
				.andRespond(withSuccess(response, MediaType.APPLICATION_JSON));

		AiWritebackProposal proposal = client.propose(
				workbook().getResource(), "B2를 12로 수정");

		assertThat(proposal.blocked()).isFalse();
		assertThat(proposal.changes()).singleElement().satisfies(change -> {
			assertThat(change.sheetName()).isEqualTo("매출현황");
			assertThat(change.oldValue()).isEqualTo(10);
			assertThat(change.contextCells()).singleElement()
					.satisfies(cell -> assertThat(cell.reference()).isEqualTo("A2"));
		});
		server.verify();
	}

	private MockMultipartFile workbook() {
		return new MockMultipartFile("file", "sales.xlsx", null, new byte[] {0x50, 0x4b});
	}

	private byte[] archive() {
		String manifest = """
				{"changed_cells":["매출현황!B2"],"checks":[],"verified":true}
				""";
		try {
			ByteArrayOutputStream output = new ByteArrayOutputStream();
			try (ZipOutputStream zip = new ZipOutputStream(output)) {
				write(zip, "workbook.xlsx", new byte[] {1, 2, 3});
				write(zip, "manifest.json", manifest.getBytes(StandardCharsets.UTF_8));
			}
			return output.toByteArray();
		}
		catch (IOException exception) {
			throw new IllegalStateException(exception);
		}
	}

	private void write(ZipOutputStream zip, String name, byte[] content) throws IOException {
		zip.putNextEntry(new ZipEntry(name));
		zip.write(content);
		zip.closeEntry();
	}
}
