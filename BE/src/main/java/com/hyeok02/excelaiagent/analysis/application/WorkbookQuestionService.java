package com.hyeok02.excelaiagent.analysis.application;

import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;
import com.hyeok02.excelaiagent.analysis.error.AnalysisNotFoundException;
import com.hyeok02.excelaiagent.analysis.error.AnalysisResultNotReadyException;
import com.hyeok02.excelaiagent.analysis.storage.AnalysisFileStorage;
import com.hyeok02.excelaiagent.integration.ai.AiServiceClient;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookQuestion;
import com.hyeok02.excelaiagent.integration.ai.NamedResource;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class WorkbookQuestionService {
	private final AnalysisJobRepository jobRepository;
	private final AnalysisFileStorage fileStorage;
	private final AiServiceClient aiServiceClient;

	public WorkbookQuestionService(
			AnalysisJobRepository jobRepository,
			AnalysisFileStorage fileStorage,
			AiServiceClient aiServiceClient) {
		this.jobRepository = jobRepository;
		this.fileStorage = fileStorage;
		this.aiServiceClient = aiServiceClient;
	}

	@Transactional(readOnly = true)
	public AiWorkbookQuestion ask(UUID analysisId, String question) {
		AnalysisJob job = jobRepository.findById(analysisId)
				.orElseThrow(() -> new AnalysisNotFoundException(analysisId));
		if (job.getStatus() != AnalysisStatus.COMPLETED) {
			throw new AnalysisResultNotReadyException(analysisId, job.getStatus());
		}
		Resource source = fileStorage.load(analysisId, job.getFileExtension());
		Resource namedSource = new NamedResource(source, job.getOriginalFilename());
		return aiServiceClient.askWorkbook(namedSource, question.trim());
	}
}
