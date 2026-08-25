package com.hyeok02.excelaiagent.analysis.application;

import java.util.UUID;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResult;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResultRepository;
import com.hyeok02.excelaiagent.analysis.error.AnalysisNotFoundException;
import com.hyeok02.excelaiagent.analysis.error.AnalysisResultNotReadyException;
import com.hyeok02.excelaiagent.analysis.error.AnalysisResultPersistenceException;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookInsights;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookSummary;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

@Service
public class AnalysisResultReader {
	private final AnalysisJobRepository jobRepository;
	private final AnalysisResultRepository resultRepository;
	private final ObjectMapper objectMapper;

	public AnalysisResultReader(AnalysisJobRepository jobRepository,
			AnalysisResultRepository resultRepository, ObjectMapper objectMapper) {
		this.jobRepository = jobRepository;
		this.resultRepository = resultRepository;
		this.objectMapper = objectMapper;
	}

	@Transactional(readOnly = true)
	public AnalysisResultDetails getResult(UUID analysisId) {
		AnalysisJob job = jobRepository.findById(analysisId)
				.orElseThrow(() -> new AnalysisNotFoundException(analysisId));
		AnalysisResult result = resultRepository.findById(analysisId)
				.orElseThrow(() -> new AnalysisResultNotReadyException(analysisId, job.getStatus()));
		return AnalysisResultDetails.from(
				analysisId, result.getCreatedAt(), deserialize(result.getResultJson()));
	}

	private AiWorkbookInsights deserialize(String json) {
		JacksonException currentFailure = null;
		try {
			AiWorkbookInsights analysis = objectMapper.readValue(json, AiWorkbookInsights.class);
			if (analysis.workbook() != null) {
				return analysis;
			}
		}
		catch (JacksonException exception) {
			currentFailure = exception;
		}
		try {
			return AiWorkbookInsights.summaryOnly(objectMapper.readValue(json, AiWorkbookSummary.class));
		}
		catch (JacksonException legacyFailure) {
			if (currentFailure != null) {
				currentFailure.addSuppressed(legacyFailure);
				throw persistenceFailure(currentFailure);
			}
			throw persistenceFailure(legacyFailure);
		}
	}

	private AnalysisResultPersistenceException persistenceFailure(JacksonException cause) {
		return new AnalysisResultPersistenceException("저장된 분석 결과를 읽지 못했습니다.", cause);
	}
}
