package com.hyeok02.excelaiagent.analysis.application;

import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisDepth;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.error.AnalysisResultPersistenceException;
import com.hyeok02.excelaiagent.analysis.error.UnreadableExcelFileException;
import com.hyeok02.excelaiagent.analysis.storage.AnalysisFileStorage;
import com.hyeok02.excelaiagent.integration.ai.AiServiceClient;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookInsights;
import com.hyeok02.excelaiagent.integration.ai.NamedResource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.Resource;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

@Service
public class AnalysisJobProcessor {

	private static final Logger log = LoggerFactory.getLogger(AnalysisJobProcessor.class);

	private final AnalysisFileStorage analysisFileStorage;
	private final AnalysisJobLifecycle lifecycle;
	private final AiServiceClient aiServiceClient;
	private final ObjectMapper objectMapper;

	public AnalysisJobProcessor(
			AnalysisFileStorage analysisFileStorage,
			AnalysisJobLifecycle lifecycle,
			AiServiceClient aiServiceClient,
			ObjectMapper objectMapper) {
		this.analysisFileStorage = analysisFileStorage;
		this.lifecycle = lifecycle;
		this.aiServiceClient = aiServiceClient;
		this.objectMapper = objectMapper;
	}

	@Async("analysisTaskExecutor")
	public void process(UUID analysisId, AnalysisDepth depth) {
		AnalysisJobLifecycle.ClaimedAnalysis analysisJob = lifecycle.claim(analysisId).orElse(null);
		if (analysisJob == null) {
			log.debug("삭제되었거나 이미 처리된 분석 작업을 건너뜁니다: {}", analysisId);
			return;
		}

		try {
			Resource file = analysisFileStorage.load(analysisId, analysisJob.fileExtension());
			Resource namedFile = new NamedResource(file, analysisJob.originalFilename());
			AiWorkbookInsights workbookAnalysis = analyzeWorkbook(
					namedFile, analysisJob.mode(), depth, analysisJob.includeHiddenSheets());
			lifecycle.complete(analysisId, serializeResult(workbookAnalysis));
		}
		catch (RuntimeException exception) {
			markFailed(analysisId, exception);
		}
	}

	private AiWorkbookInsights analyzeWorkbook(
			Resource file,
			AnalysisMode mode,
			AnalysisDepth depth,
			boolean includeHiddenSheets) {
		if (mode == AnalysisMode.LLM) {
			return aiServiceClient.generateWorkbookInsights(file, depth, includeHiddenSheets);
		}
		return AiWorkbookInsights.summaryOnly(
				aiServiceClient.summarizeWorkbook(file, includeHiddenSheets));
	}

	private String serializeResult(AiWorkbookInsights workbookAnalysis) {
		try {
			return objectMapper.writeValueAsString(workbookAnalysis);
		}
		catch (JacksonException exception) {
			throw new AnalysisResultPersistenceException("분석 결과를 저장 형식으로 변환하지 못했습니다.", exception);
		}
	}

	private void markFailed(UUID analysisId, RuntimeException cause) {
		try {
			String userMessage = cause instanceof UnreadableExcelFileException
					? cause.getMessage() : null;
			lifecycle.fail(analysisId, userMessage);
		}
		catch (RuntimeException statusException) {
			cause.addSuppressed(statusException);
		}
		log.error("Excel 분석 작업에 실패했습니다: {}", analysisId, cause);
	}
}
