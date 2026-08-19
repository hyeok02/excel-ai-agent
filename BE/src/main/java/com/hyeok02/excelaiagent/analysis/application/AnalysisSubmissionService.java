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
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookInsights;
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
			AiWorkbookInsights workbookAnalysis = analyzeWorkbook(file, mode);
			AnalysisResult analysisResult = AnalysisResult.completed(
					analysisId,
					serializeResult(workbookAnalysis),
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

	private AiWorkbookInsights analyzeWorkbook(MultipartFile file, AnalysisMode mode) {
		if (mode == AnalysisMode.LLM) {
			return aiServiceClient.generateWorkbookInsights(file);
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

	private AiWorkbookInsights deserializeResult(String resultJson) {
		JacksonException currentFormatException = null;
		try {
			AiWorkbookInsights workbookAnalysis = objectMapper.readValue(resultJson, AiWorkbookInsights.class);
			if (workbookAnalysis.workbook() != null) {
				return workbookAnalysis;
			}
		}
		catch (JacksonException exception) {
			currentFormatException = exception;
		}

		try {
			AiWorkbookSummary workbookSummary = objectMapper.readValue(resultJson, AiWorkbookSummary.class);
			return AiWorkbookInsights.summaryOnly(workbookSummary);
		}
		catch (JacksonException legacyException) {
			if (currentFormatException != null) {
				currentFormatException.addSuppressed(legacyException);
				throw new AnalysisResultPersistenceException(
						"저장된 분석 결과를 읽지 못했습니다.", currentFormatException);
			}
			throw new AnalysisResultPersistenceException("저장된 분석 결과를 읽지 못했습니다.", legacyException);
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
