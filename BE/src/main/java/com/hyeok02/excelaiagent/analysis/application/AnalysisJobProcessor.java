package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisDepth;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResult;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResultRepository;
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
	private final AnalysisJobRepository analysisJobRepository;
	private final AnalysisResultRepository analysisResultRepository;
	private final AiServiceClient aiServiceClient;
	private final ObjectMapper objectMapper;

	public AnalysisJobProcessor(
			AnalysisFileStorage analysisFileStorage,
			AnalysisJobRepository analysisJobRepository,
			AnalysisResultRepository analysisResultRepository,
			AiServiceClient aiServiceClient,
			ObjectMapper objectMapper) {
		this.analysisFileStorage = analysisFileStorage;
		this.analysisJobRepository = analysisJobRepository;
		this.analysisResultRepository = analysisResultRepository;
		this.aiServiceClient = aiServiceClient;
		this.objectMapper = objectMapper;
	}

	@Async("analysisTaskExecutor")
	public void process(UUID analysisId, AnalysisDepth depth) {
		AnalysisJob analysisJob = analysisJobRepository.findById(analysisId).orElse(null);
		if (analysisJob == null) {
			log.warn("접수된 분석 작업을 찾지 못했습니다: {}", analysisId);
			return;
		}

		try {
			analysisJob.markProcessing(Instant.now());
			analysisJobRepository.saveAndFlush(analysisJob);

			Resource file = analysisFileStorage.load(analysisId, analysisJob.getFileExtension());
			Resource namedFile = new NamedResource(file, analysisJob.getOriginalFilename());
			AiWorkbookInsights workbookAnalysis = analyzeWorkbook(namedFile, analysisJob.getMode(), depth);
			AnalysisResult analysisResult = AnalysisResult.completed(
					analysisId,
					serializeResult(workbookAnalysis),
					Instant.now());
			analysisResultRepository.saveAndFlush(analysisResult);
			analysisJob.markCompleted(Instant.now());
			analysisJobRepository.saveAndFlush(analysisJob);
		}
		catch (RuntimeException exception) {
			markFailed(analysisJob, exception);
		}
	}

	private AiWorkbookInsights analyzeWorkbook(
			Resource file,
			AnalysisMode mode,
			AnalysisDepth depth) {
		if (mode == AnalysisMode.LLM) {
			return aiServiceClient.generateWorkbookInsights(file, depth);
		}
		return AiWorkbookInsights.summaryOnly(aiServiceClient.summarizeWorkbook(file));
	}

	private String serializeResult(AiWorkbookInsights workbookAnalysis) {
		try {
			return objectMapper.writeValueAsString(workbookAnalysis);
		}
		catch (JacksonException exception) {
			throw new AnalysisResultPersistenceException("분석 결과를 저장 형식으로 변환하지 못했습니다.", exception);
		}
	}

	private void markFailed(AnalysisJob analysisJob, RuntimeException cause) {
		try {
			String userMessage = cause instanceof UnreadableExcelFileException
					? cause.getMessage() : null;
			analysisJob.markFailed(Instant.now(), userMessage);
			analysisJobRepository.saveAndFlush(analysisJob);
		}
		catch (RuntimeException statusException) {
			cause.addSuppressed(statusException);
		}
		log.error("Excel 분석 작업에 실패했습니다: {}", analysisJob.getAnalysisId(), cause);
	}
}
