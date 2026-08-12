package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.error.AnalysisNotFoundException;
import com.hyeok02.excelaiagent.analysis.storage.AnalysisFileStorage;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

@Service
public class AnalysisSubmissionService {

	private final ExcelFileValidator excelFileValidator;
	private final AnalysisFileStorage analysisFileStorage;
	private final AnalysisJobRepository analysisJobRepository;

	public AnalysisSubmissionService(
			ExcelFileValidator excelFileValidator,
			AnalysisFileStorage analysisFileStorage,
			AnalysisJobRepository analysisJobRepository) {
		this.excelFileValidator = excelFileValidator;
		this.analysisFileStorage = analysisFileStorage;
		this.analysisJobRepository = analysisJobRepository;
	}

	@Transactional
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

		analysisJobRepository.saveAndFlush(analysisJob);
		analysisFileStorage.store(analysisId, validatedFile.extension(), file);

		return new AnalysisSubmission(
				analysisJob.getAnalysisId(),
				analysisJob.getStatus(),
				analysisJob.getMode(),
				analysisJob.getOriginalFilename(),
				analysisJob.getFileSizeBytes(),
				analysisJob.getCreatedAt());
	}

	@Transactional(readOnly = true)
	public AnalysisDetails getDetails(UUID analysisId) {
		AnalysisJob analysisJob = analysisJobRepository.findById(analysisId)
				.orElseThrow(() -> new AnalysisNotFoundException(analysisId));
		return toDetails(analysisJob);
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
