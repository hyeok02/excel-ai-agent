package com.hyeok02.excelaiagent.writeback.application;

import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.storage.AnalysisFileStorage;
import com.hyeok02.excelaiagent.integration.ai.NamedResource;
import com.hyeok02.excelaiagent.writeback.domain.WorkbookWriteback;
import com.hyeok02.excelaiagent.writeback.domain.WorkbookWritebackRepository;
import com.hyeok02.excelaiagent.writeback.domain.WritebackStatus;
import org.springframework.core.io.Resource;

/** 이번 수정이 올라탈 파일을 고른다. */
final class WritebackSources {
	private final WorkbookWritebackRepository writebackRepository;
	private final AnalysisFileStorage fileStorage;

	WritebackSources(
			WorkbookWritebackRepository writebackRepository, AnalysisFileStorage fileStorage) {
		this.writebackRepository = writebackRepository;
		this.fileStorage = fileStorage;
	}

	/** 가장 마지막으로 적용된 수정본. 아직 하나도 없으면 비어 있다. */
	UUID latestApplied(UUID analysisId) {
		return writebackRepository
				.findFirstByAnalysisIdAndStatusOrderByUpdatedAtDesc(
						analysisId, WritebackStatus.APPLIED)
				.map(WorkbookWriteback::getWritebackId)
				.orElse(null);
	}

	/**
	 * 이번 수정이 올라탈 파일.
	 *
	 * 직전 수정본이 있으면 그 결과 위에 이어서 고친다. 늘 원본에서 다시 시작하면
	 * 앞선 수정이 빠진 사본이 나온다.
	 */
	Resource of(AnalysisJob job, UUID baseWritebackId) {
		Resource content = baseWritebackId == null
				? fileStorage.load(job.getAnalysisId(), job.getFileExtension())
				: fileStorage.loadWriteback(
						job.getAnalysisId(), baseWritebackId, job.getFileExtension());
		return new NamedResource(content, job.getOriginalFilename());
	}
}
