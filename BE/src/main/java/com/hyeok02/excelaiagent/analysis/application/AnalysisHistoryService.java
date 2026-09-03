package com.hyeok02.excelaiagent.analysis.application;

import java.util.UUID;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AnalysisHistoryService {
	private final AnalysisJobRepository repository;
	private final AnalysisAccessService accessService;

	public AnalysisHistoryService(
			AnalysisJobRepository repository,
			AnalysisAccessService accessService) {
		this.repository = repository;
		this.accessService = accessService;
	}

	@Transactional(readOnly = true)
	public AnalysisDetails getDetails(UUID analysisId, String ownerUsername) {
		return toDetails(accessService.requireOwned(analysisId, ownerUsername));
	}

	@Transactional(readOnly = true)
	public AnalysisHistoryPage getHistory(
			String ownerUsername, AnalysisMode mode, String filename, int page, int size) {
		PageRequest request = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
		Page<AnalysisJob> jobs = search(ownerUsername, mode, normalize(filename), request);
		return new AnalysisHistoryPage(
				jobs.getContent().stream().map(this::toDetails).toList(),
				jobs.getNumber(), jobs.getSize(), jobs.getTotalElements(),
				jobs.getTotalPages(), jobs.hasNext());
	}

	private Page<AnalysisJob> search(
			String ownerUsername, AnalysisMode mode, String filename, PageRequest request) {
		if (mode != null && filename != null) {
			return repository.findByOwnerUsernameAndModeAndOriginalFilenameContainingIgnoreCase(
					ownerUsername, mode, filename, request);
		}
		if (mode != null) {
			return repository.findByOwnerUsernameAndMode(ownerUsername, mode, request);
		}
		if (filename != null) {
			return repository.findByOwnerUsernameAndOriginalFilenameContainingIgnoreCase(
					ownerUsername, filename, request);
		}
		return repository.findByOwnerUsername(ownerUsername, request);
	}

	private String normalize(String filename) {
		return filename == null || filename.isBlank() ? null : filename.trim();
	}

	private AnalysisDetails toDetails(AnalysisJob job) {
		return new AnalysisDetails(
				job.getAnalysisId(), job.getStatus(), job.getMode(), job.getOriginalFilename(),
				job.getFileExtension(), job.getFileSizeBytes(), accessService.sourceAvailable(job),
				job.getCreatedAt(), job.getUpdatedAt());
	}
}
