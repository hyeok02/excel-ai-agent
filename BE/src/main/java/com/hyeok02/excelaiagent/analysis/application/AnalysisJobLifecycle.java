package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResult;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResultRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Short transactions coordinate workers with deletion; no lock is held during AI calls. */
@Service
public class AnalysisJobLifecycle {

	private final AnalysisJobRepository jobs;
	private final AnalysisResultRepository results;

	public AnalysisJobLifecycle(AnalysisJobRepository jobs, AnalysisResultRepository results) {
		this.jobs = jobs;
		this.results = results;
	}

	@Transactional
	public Optional<ClaimedAnalysis> claim(UUID analysisId) {
		return jobs.findForUpdate(analysisId)
				.filter(job -> job.getStatus() == AnalysisStatus.QUEUED)
				.map(job -> {
					job.markProcessing(Instant.now());
					return new ClaimedAnalysis(job.getFileExtension(), job.getOriginalFilename(),
							job.getMode(), job.isIncludeHiddenSheets());
				});
	}

	@Transactional
	public boolean complete(UUID analysisId, String resultJson) {
		AnalysisJob job = processing(analysisId);
		if (job == null) {
			return false;
		}
		Instant now = Instant.now();
		results.saveAndFlush(AnalysisResult.completed(analysisId, resultJson, now));
		job.markCompleted(now);
		return true;
	}

	@Transactional
	public boolean fail(UUID analysisId, String userMessage) {
		AnalysisJob job = processing(analysisId);
		if (job == null) {
			return false;
		}
		job.markFailed(Instant.now(), userMessage);
		return true;
	}

	private AnalysisJob processing(UUID analysisId) {
		return jobs.findForUpdate(analysisId)
				.filter(job -> job.getStatus() == AnalysisStatus.PROCESSING).orElse(null);
	}

	/** Only immutable input metadata leaves the claim transaction, never a detached entity to save. */
	public record ClaimedAnalysis(
			String fileExtension, String originalFilename, AnalysisMode mode,
			boolean includeHiddenSheets) {
	}
}
