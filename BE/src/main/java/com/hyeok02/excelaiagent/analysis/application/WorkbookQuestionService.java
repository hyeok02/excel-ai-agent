package com.hyeok02.excelaiagent.analysis.application;

import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;
import com.hyeok02.excelaiagent.analysis.error.AnalysisResultNotReadyException;
import com.hyeok02.excelaiagent.analysis.storage.AnalysisFileStorage;
import com.hyeok02.excelaiagent.integration.ai.AiServiceClient;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookQuestion;
import com.hyeok02.excelaiagent.integration.ai.NamedResource;
import com.hyeok02.excelaiagent.integration.ai.WorkbookQuestionContext;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;

@Service
public class WorkbookQuestionService {
	private final AnalysisAccessService accessService;
	private final AnalysisFileStorage fileStorage;
	private final AiServiceClient aiServiceClient;
	private final WorkbookQuestionHistoryService historyService;

	public WorkbookQuestionService(
			AnalysisAccessService accessService,
			AnalysisFileStorage fileStorage,
			AiServiceClient aiServiceClient,
			WorkbookQuestionHistoryService historyService) {
		this.accessService = accessService;
		this.fileStorage = fileStorage;
		this.aiServiceClient = aiServiceClient;
		this.historyService = historyService;
	}

	/**
	 * 트랜잭션을 열어 두지 않는다.
	 *
	 * AI 응답은 최대 150초가 걸리는데 그동안 DB 커넥션을 쥐고 있으면 질문 몇 건이
	 * 풀을 모두 가져가 로그인까지 막힌다. 소유권 확인이 그 자체로 짧은 트랜잭션을
	 * 열고 닫는다. 응답을 받은 뒤 이력 저장만 별도의 짧은 트랜잭션으로 처리한다.
	 */
	public AiWorkbookQuestion ask(UUID analysisId, String question, String ownerUsername) {
		return ask(analysisId, question, ownerUsername, null);
	}

	public AiWorkbookQuestion ask(
			UUID analysisId, String question, String ownerUsername, WorkbookQuestionContext context) {
		AnalysisJob job = accessService.requireOwned(analysisId, ownerUsername);
		if (job.getStatus() != AnalysisStatus.COMPLETED) {
			throw new AnalysisResultNotReadyException(analysisId, job.getStatus());
		}
		accessService.requireSourceAvailable(job);
		Resource source = fileStorage.load(analysisId, job.getFileExtension());
		Resource namedSource = new NamedResource(source, job.getOriginalFilename());
		AiWorkbookQuestion answer = context != null
				? aiServiceClient.askWorkbook(namedSource, question.trim(), job.isIncludeHiddenSheets(), context)
				: aiServiceClient.askWorkbook(namedSource, question.trim(), job.isIncludeHiddenSheets());
		historyService.save(analysisId, ownerUsername, question.trim(), answer);
		return answer;
	}
}
