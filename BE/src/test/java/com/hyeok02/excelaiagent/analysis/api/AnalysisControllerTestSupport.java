package com.hyeok02.excelaiagent.analysis.api;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.when;

import com.hyeok02.excelaiagent.BackendApplication;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResultRepository;
import com.hyeok02.excelaiagent.analysis.storage.AnalysisFileStorage;
import com.hyeok02.excelaiagent.integration.ai.AiServiceClient;
import com.hyeok02.excelaiagent.integration.ai.AiWritebackClient;
import com.hyeok02.excelaiagent.writeback.domain.WorkbookWritebackRepository;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.core.io.Resource;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest(classes = BackendApplication.class,
		properties = "app.storage.upload-dir=build/test-uploads")
@AutoConfigureMockMvc
abstract class AnalysisControllerTestSupport {
	protected static final byte[] ZIP_FILE = {0x50, 0x4b, 0x03, 0x04, 0x01};

	@Autowired protected MockMvc mockMvc;
	@Autowired protected AnalysisJobRepository analysisJobRepository;
	@Autowired protected AnalysisResultRepository analysisResultRepository;
	@Autowired protected AnalysisFileStorage analysisFileStorage;
	@Autowired protected WorkbookWritebackRepository workbookWritebackRepository;
	@MockitoBean protected AiServiceClient aiServiceClient;
	@MockitoBean protected AiWritebackClient aiWritebackClient;

	@BeforeEach
	void prepare() {
		workbookWritebackRepository.deleteAll();
		analysisJobRepository.deleteAll();
		reset(aiServiceClient, aiWritebackClient);
		when(aiServiceClient.summarizeWorkbook(any(Resource.class)))
				.thenReturn(AnalysisWorkbookFixture.summary());
		when(aiServiceClient.generateWorkbookInsights(any(Resource.class), any()))
				.thenReturn(AnalysisWorkbookFixture.insights());
	}

	protected MockMultipartFile excel(String filename) {
		return new MockMultipartFile("file", filename, null, ZIP_FILE);
	}
}
