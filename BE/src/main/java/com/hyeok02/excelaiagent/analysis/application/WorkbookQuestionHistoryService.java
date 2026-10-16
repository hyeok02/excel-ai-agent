package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.WorkbookQuestion;
import com.hyeok02.excelaiagent.analysis.domain.WorkbookQuestionRepository;
import com.hyeok02.excelaiagent.analysis.error.AnalysisNotFoundException;
import com.hyeok02.excelaiagent.analysis.error.AnalysisResultPersistenceException;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookQuestion;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

@Service
public class WorkbookQuestionHistoryService {
	private final WorkbookQuestionRepository repository;
	private final AnalysisJobRepository jobRepository;
	private final AnalysisAccessService accessService;
	private final ObjectMapper objectMapper;

	public WorkbookQuestionHistoryService(
			WorkbookQuestionRepository repository, AnalysisJobRepository jobRepository,
			AnalysisAccessService accessService, ObjectMapper objectMapper) {
		this.repository = repository;
		this.jobRepository = jobRepository;
		this.accessService = accessService;
		this.objectMapper = objectMapper;
	}

	/** Called only after the external AI request completes; never keeps a connection during inference. */
	@Transactional
	public void save(UUID analysisId, String ownerUsername, String submittedQuestion, AiWorkbookQuestion answer) {
		// Recheck ownership after inference and serialize with deletion of the parent analysis.
		jobRepository.findOwnedForQuestionSave(analysisId, ownerUsername)
				.orElseThrow(() -> new AnalysisNotFoundException(analysisId));
		try {
			repository.saveAndFlush(WorkbookQuestion.answered(
					analysisId, submittedQuestion, objectMapper.writeValueAsString(answer), Instant.now()));
		}
		catch (JacksonException exception) {
			throw new AnalysisResultPersistenceException("질문과 답변을 저장하지 못했습니다.", exception);
		}
	}

	@Transactional(readOnly = true)
	public WorkbookQuestionHistoryPage getHistory(
			UUID analysisId, String ownerUsername, Long before, int size) {
		accessService.requireOwned(analysisId, ownerUsername);
		// History remains readable after the original workbook expires. No source or AI access here.
		PageRequest request = PageRequest.of(0, size + 1);
		List<WorkbookQuestion> rows = before == null
				? repository.findByAnalysisIdOrderByIdDesc(analysisId, request)
				: repository.findByAnalysisIdAndIdLessThanOrderByIdDesc(analysisId, before, request);
		boolean hasMore = rows.size() > size;
		List<WorkbookQuestion> selected = rows.subList(0, Math.min(size, rows.size()));
		String nextCursor = hasMore ? selected.getLast().getId().toString() : null;
		List<WorkbookQuestionHistoryPage.Item> items = new ArrayList<>(selected.size());
		for (WorkbookQuestion row : selected) {
			items.add(new WorkbookQuestionHistoryPage.Item(
					row.getId().toString(), row.getCreatedAt(), deserialize(row.getAnswerJson())));
		}
		Collections.reverse(items);
		return new WorkbookQuestionHistoryPage(List.copyOf(items), nextCursor);
	}

	private AiWorkbookQuestion deserialize(String json) {
		try {
			return objectMapper.readValue(json, AiWorkbookQuestion.class);
		}
		catch (JacksonException exception) {
			throw new AnalysisResultPersistenceException("저장된 질문과 답변을 읽지 못했습니다.", exception);
		}
	}
}
