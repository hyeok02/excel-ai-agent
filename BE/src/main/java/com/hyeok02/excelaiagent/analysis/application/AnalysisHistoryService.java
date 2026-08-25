package com.hyeok02.excelaiagent.analysis.application;

import java.util.UUID;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.error.AnalysisNotFoundException;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AnalysisHistoryService {
	private final AnalysisJobRepository repository;

	public AnalysisHistoryService(AnalysisJobRepository repository) {
		this.repository = repository;
	}

	@Transactional(readOnly = true)
	public AnalysisDetails getDetails(UUID analysisId) {
		return toDetails(repository.findById(analysisId)
				.orElseThrow(() -> new AnalysisNotFoundException(analysisId)));
	}

	@Transactional(readOnly = true)
	public AnalysisHistoryPage getHistory(AnalysisMode mode, String filename, int page, int size) {
		PageRequest request = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
		Page<AnalysisJob> jobs = search(mode, normalize(filename), request);
		return new AnalysisHistoryPage(
				jobs.getContent().stream().map(this::toDetails).toList(),
				jobs.getNumber(), jobs.getSize(), jobs.getTotalElements(),
				jobs.getTotalPages(), jobs.hasNext());
	}

	private Page<AnalysisJob> search(AnalysisMode mode, String filename, PageRequest request) {
		if (mode != null && filename != null) {
			return repository.findByModeAndOriginalFilenameContainingIgnoreCase(mode, filename, request);
		}
		if (mode != null) {
			return repository.findByMode(mode, request);
		}
		if (filename != null) {
			return repository.findByOriginalFilenameContainingIgnoreCase(filename, request);
		}
		return repository.findAll(request);
	}

	private String normalize(String filename) {
		return filename == null || filename.isBlank() ? null : filename.trim();
	}

	private AnalysisDetails toDetails(AnalysisJob job) {
		return new AnalysisDetails(
				job.getAnalysisId(), job.getStatus(), job.getMode(), job.getOriginalFilename(),
				job.getFileExtension(), job.getFileSizeBytes(), job.getCreatedAt(), job.getUpdatedAt());
	}
}
