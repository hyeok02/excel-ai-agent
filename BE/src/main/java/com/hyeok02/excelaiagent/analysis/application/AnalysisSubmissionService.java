package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisDepth;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.storage.AnalysisFileStorage;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

@Service
public class AnalysisSubmissionService {
	private final ExcelFileValidator excelFileValidator;
	private final AnalysisFileStorage analysisFileStorage;
	private final AnalysisJobRepository analysisJobRepository;
	private final AnalysisJobProcessor analysisJobProcessor;
	private final AnalysisResultReader analysisResultReader;
	private final AnalysisHistoryService analysisHistoryService;
	private final AnalysisAccessService analysisAccessService;

	public AnalysisSubmissionService(
			ExcelFileValidator excelFileValidator,
			AnalysisFileStorage analysisFileStorage,
			AnalysisJobRepository analysisJobRepository,
			AnalysisJobProcessor analysisJobProcessor,
			AnalysisResultReader analysisResultReader,
			AnalysisHistoryService analysisHistoryService,
			AnalysisAccessService analysisAccessService) {
		this.excelFileValidator = excelFileValidator;
		this.analysisFileStorage = analysisFileStorage;
		this.analysisJobRepository = analysisJobRepository;
		this.analysisJobProcessor = analysisJobProcessor;
		this.analysisResultReader = analysisResultReader;
		this.analysisHistoryService = analysisHistoryService;
		this.analysisAccessService = analysisAccessService;
	}

	public AnalysisSubmission submit(
			MultipartFile file, AnalysisMode mode, AnalysisDepth depth, String ownerUsername) {
		ValidatedExcelFile validatedFile = excelFileValidator.validate(file);
		UUID analysisId = UUID.randomUUID();
		AnalysisJob job = AnalysisJob.queued(
				analysisId, mode, validatedFile.originalFilename(), validatedFile.extension(),
				validatedFile.sizeBytes(), ownerUsername, Instant.now());
		analysisFileStorage.store(analysisId, validatedFile.extension(), file);
		try {
			job = analysisJobRepository.saveAndFlush(job);
		}
		catch (RuntimeException exception) {
			analysisFileStorage.delete(analysisId);
			throw exception;
		}
		AnalysisSubmission submission = new AnalysisSubmission(
				job.getAnalysisId(), job.getStatus(), job.getMode(),
				job.getOriginalFilename(), job.getFileSizeBytes(), job.getCreatedAt());
		analysisJobProcessor.process(analysisId, depth);
		return submission;
	}

	public AnalysisResultDetails getResult(UUID analysisId, String ownerUsername) {
		return analysisResultReader.getResult(analysisId, ownerUsername);
	}

	public AnalysisDetails getDetails(UUID analysisId, String ownerUsername) {
		return analysisHistoryService.getDetails(analysisId, ownerUsername);
	}

	public AnalysisHistoryPage getHistory(
			String ownerUsername, AnalysisMode mode, String filename, int page, int size) {
		return analysisHistoryService.getHistory(ownerUsername, mode, filename, page, size);
	}

	@Transactional
	public void delete(UUID analysisId, String ownerUsername) {
		AnalysisJob job = analysisAccessService.requireOwned(analysisId, ownerUsername);
		analysisJobRepository.delete(job);
		analysisJobRepository.flush();
		analysisFileStorage.delete(analysisId);
	}
}
