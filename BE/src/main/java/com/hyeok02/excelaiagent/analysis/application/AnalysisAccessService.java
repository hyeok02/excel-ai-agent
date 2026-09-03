package com.hyeok02.excelaiagent.analysis.application;

import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.error.AnalysisNotFoundException;
import com.hyeok02.excelaiagent.analysis.error.AnalysisSourceUnavailableException;
import com.hyeok02.excelaiagent.analysis.storage.AnalysisFileStorage;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AnalysisAccessService {
	private final AnalysisJobRepository repository;
	private final AnalysisFileStorage fileStorage;

	public AnalysisAccessService(
			AnalysisJobRepository repository,
			AnalysisFileStorage fileStorage) {
		this.repository = repository;
		this.fileStorage = fileStorage;
	}

	@Transactional(readOnly = true)
	public AnalysisJob requireOwned(UUID analysisId, String ownerUsername) {
		return repository.findByAnalysisIdAndOwnerUsername(analysisId, ownerUsername)
				.orElseThrow(() -> new AnalysisNotFoundException(analysisId));
	}

	public AnalysisJob requireSourceAvailable(AnalysisJob job) {
		if (!sourceAvailable(job)) {
			throw new AnalysisSourceUnavailableException(job.getAnalysisId());
		}
		return job;
	}

	public boolean sourceAvailable(AnalysisJob job) {
		return fileStorage.exists(job.getAnalysisId(), job.getFileExtension());
	}
}
