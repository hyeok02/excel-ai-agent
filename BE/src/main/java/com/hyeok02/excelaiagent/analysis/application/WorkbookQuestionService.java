package com.hyeok02.excelaiagent.analysis.application;

import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;
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
	private final AnalysisAccessService accessService;
	private final AnalysisFileStorage fileStorage;
	private final AiServiceClient aiServiceClient;

	public WorkbookQuestionService(
			AnalysisAccessService accessService,
			AnalysisFileStorage fileStorage,
			AiServiceClient aiServiceClient) {
		this.accessService = accessService;
		this.fileStorage = fileStorage;
		this.aiServiceClient = aiServiceClient;
	}

	@Transactional(readOnly = true)
	public AiWorkbookQuestion ask(UUID analysisId, String question, String ownerUsername) {
		AnalysisJob job = accessService.requireOwned(analysisId, ownerUsername);
		if (job.getStatus() != AnalysisStatus.COMPLETED) {
			throw new AnalysisResultNotReadyException(analysisId, job.getStatus());
		}
		accessService.requireSourceAvailable(job);
		Resource source = fileStorage.load(analysisId, job.getFileExtension());
		Resource namedSource = new NamedResource(source, job.getOriginalFilename());
		return aiServiceClient.askWorkbook(namedSource, question.trim());
	}
}
