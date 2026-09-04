package com.hyeok02.excelaiagent.analysis.api;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;

import java.util.List;

import com.hyeok02.excelaiagent.integration.ai.AiWritebackManifest;
import com.hyeok02.excelaiagent.integration.ai.AiWritebackPackage;
import com.hyeok02.excelaiagent.integration.ai.AiWritebackProposal;
import com.jayway.jsonpath.JsonPath;

abstract class WorkbookWritebackTestSupport extends AnalysisControllerTestSupport {

	protected String submitCompleted() throws Exception {
		return submitCompleted("system");
	}

	protected String submitCompleted(String username) throws Exception {
		String body = mockMvc.perform(multipart("/api/v1/analyses")
					.file(excel("sales.xlsx")).param("mode", "BFS")
					.with(user(username)))
				.andReturn().getResponse().getContentAsString();
		return JsonPath.read(body, "$.analysisId");
	}

	protected AiWritebackProposal proposal(boolean blocked) {
		List<AiWritebackProposal.Change> changes = blocked ? List.of() : List.of(
				new AiWritebackProposal.Change("매출현황", "B2", 12, "정정", 10, List.of()));
		return new AiWritebackProposal("B2 수정", blocked ? "blocked" : "ready",
				"변경 제안", changes, blocked ? List.of("수식 셀") : List.of(), List.of());
	}

	protected AiWritebackPackage packageResult() {
		AiWritebackManifest manifest = new AiWritebackManifest(
				List.of("매출현황!B2"),
				List.of(new AiWritebackManifest.Check("formulas", true, "수식 보존")), true);
		return new AiWritebackPackage(new byte[] {1, 2, 3}, manifest);
	}
}
