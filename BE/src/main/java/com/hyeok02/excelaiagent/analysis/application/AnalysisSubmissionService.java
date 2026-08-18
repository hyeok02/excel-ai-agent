package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResult;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResultRepository;
import com.hyeok02.excelaiagent.analysis.error.AnalysisNotFoundException;
import com.hyeok02.excelaiagent.analysis.error.AnalysisResultNotReadyException;
import com.hyeok02.excelaiagent.analysis.error.AnalysisResultPersistenceException;
import com.hyeok02.excelaiagent.analysis.storage.AnalysisFileStorage;
import com.hyeok02.excelaiagent.integration.ai.AiServiceClient;
import com.hyeok02.excelaiagent.integration.ai.AiServiceUnavailableException;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookSummary;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

@Service
public class AnalysisSubmissionService {

	private final ExcelFileValidator excelFileValidator;
	private final AnalysisFileStorage analysisFileStorage;
	private final AnalysisJobRepository analysisJobRepository;
	private final AnalysisResultRepository analysisResultRepository;
	private final AiServiceClient aiServiceClient;
	private final ObjectMapper objectMapper;

	public AnalysisSubmissionService(
			ExcelFileValidator excelFileValidator,
			AnalysisFileStorage analysisFileStorage,
			AnalysisJobRepository analysisJobRepository,
			AnalysisResultRepository analysisResultRepository,
			AiServiceClient aiServiceClient,
			ObjectMapper objectMapper) {
		this.excelFileValidator = excelFileValidator;
		this.analysisFileStorage = analysisFileStorage;
		this.analysisJobRepository = analysisJobRepository;
		this.analysisResultRepository = analysisResultRepository;
		this.aiServiceClient = aiServiceClient;
		this.objectMapper = objectMapper;
	}

	public AnalysisSubmission submit(MultipartFile file, AnalysisMode mode) {
		ValidatedExcelFile validatedFile = excelFileValidator.validate(file);
		UUID analysisId = UUID.randomUUID();
		Instant now = Instant.now();
		AnalysisJob analysisJob = AnalysisJob.queued(
				analysisId,
				mode,
				validatedFile.originalFilename(),
				validatedFile.extension(),
				validatedFile.sizeBytes(),
				now);

		analysisFileStorage.store(analysisId, validatedFile.extension(), file);
		try {
			analysisJob = analysisJobRepository.saveAndFlush(analysisJob);
		}
		catch (RuntimeException exception) {
			analysisFileStorage.delete(analysisId);
			throw exception;
		}

		analysisJob.markProcessing(Instant.now());
		analysisJobRepository.saveAndFlush(analysisJob);

		try {
			AiWorkbookSummary workbookSummary = aiServiceClient.summarizeWorkbook(file);
			AnalysisResult analysisResult = AnalysisResult.completed(
					analysisId,
					serializeResult(workbookSummary),
					Instant.now());
			analysisResultRepository.saveAndFlush(analysisResult);
			analysisJob.markCompleted(Instant.now());
			analysisJobRepository.saveAndFlush(analysisJob);
		}
		catch (AiServiceUnavailableException | AnalysisResultPersistenceException exception) {
			analysisJob.markFailed(Instant.now());
			analysisJobRepository.saveAndFlush(analysisJob);
			throw exception;
		}

		return new AnalysisSubmission(
				analysisJob.getAnalysisId(),
				analysisJob.getStatus(),
				analysisJob.getMode(),
				analysisJob.getOriginalFilename(),
				analysisJob.getFileSizeBytes(),
				analysisJob.getCreatedAt());
	}

	@Transactional(readOnly = true)
	public AnalysisResultDetails getResult(UUID analysisId) {
		AnalysisJob analysisJob = analysisJobRepository.findById(analysisId)
				.orElseThrow(() -> new AnalysisNotFoundException(analysisId));
		AnalysisResult analysisResult = analysisResultRepository.findById(analysisId)
				.orElseThrow(() -> new AnalysisResultNotReadyException(analysisId, analysisJob.getStatus()));

		return AnalysisResultDetails.from(
				analysisId,
				analysisResult.getCreatedAt(),
				deserializeResult(analysisResult.getResultJson()));
	}

	@Transactional(readOnly = true)
	public AnalysisDetails getDetails(UUID analysisId) {
		AnalysisJob analysisJob = analysisJobRepository.findById(analysisId)
				.orElseThrow(() -> new AnalysisNotFoundException(analysisId));
		return toDetails(analysisJob);
	}

	@Transactional
	public void delete(UUID analysisId) {
		AnalysisJob analysisJob = analysisJobRepository.findById(analysisId)
				.orElseThrow(() -> new AnalysisNotFoundException(analysisId));

		analysisJobRepository.delete(analysisJob);
		analysisJobRepository.flush();
		analysisFileStorage.delete(analysisId);
	}

	@Transactional(readOnly = true)
	public AnalysisHistoryPage getHistory(AnalysisMode mode, String filename, int page, int size) {
		PageRequest pageRequest = PageRequest.of(
				page,
				size,
				Sort.by(Sort.Direction.DESC, "createdAt"));
		String normalizedFilename = normalizeFilename(filename);
		Page<AnalysisJob> analysisJobs = searchHistory(mode, normalizedFilename, pageRequest);

		return new AnalysisHistoryPage(
				analysisJobs.getContent().stream().map(this::toDetails).toList(),
				analysisJobs.getNumber(),
				analysisJobs.getSize(),
				analysisJobs.getTotalElements(),
				analysisJobs.getTotalPages(),
				analysisJobs.hasNext());
	}

	private Page<AnalysisJob> searchHistory(
			AnalysisMode mode,
			String filename,
			PageRequest pageRequest) {
		if (mode != null && filename != null) {
			return analysisJobRepository.findByModeAndOriginalFilenameContainingIgnoreCase(
					mode,
					filename,
					pageRequest);
		}
		if (mode != null) {
			return analysisJobRepository.findByMode(mode, pageRequest);
		}
		if (filename != null) {
			return analysisJobRepository.findByOriginalFilenameContainingIgnoreCase(filename, pageRequest);
		}
		return analysisJobRepository.findAll(pageRequest);
	}

	private String normalizeFilename(String filename) {
		if (filename == null || filename.isBlank()) {
			return null;
		}
		return filename.trim();
	}

	private String serializeResult(AiWorkbookSummary workbookSummary) {
		try {
			return objectMapper.writeValueAsString(workbookSummary);
		}
		catch (JacksonException exception) {
			throw new AnalysisResultPersistenceException("분석 결과를 저장 형식으로 변환하지 못했습니다.", exception);
		}
	}

	private AiWorkbookSummary deserializeResult(String resultJson) {
		try {
			return objectMapper.readValue(resultJson, AiWorkbookSummary.class);
		}
		catch (JacksonException exception) {
			throw new AnalysisResultPersistenceException("저장된 분석 결과를 읽지 못했습니다.", exception);
		}
	}

	private AnalysisDetails toDetails(AnalysisJob analysisJob) {
		return new AnalysisDetails(
				analysisJob.getAnalysisId(),
				analysisJob.getStatus(),
				analysisJob.getMode(),
				analysisJob.getOriginalFilename(),
				analysisJob.getFileExtension(),
				analysisJob.getFileSizeBytes(),
				analysisJob.getCreatedAt(),
				analysisJob.getUpdatedAt());
	}
}
