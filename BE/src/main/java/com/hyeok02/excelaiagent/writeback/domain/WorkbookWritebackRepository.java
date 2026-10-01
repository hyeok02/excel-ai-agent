package com.hyeok02.excelaiagent.writeback.domain;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

public interface WorkbookWritebackRepository extends JpaRepository<WorkbookWriteback, UUID> {
	List<WorkbookWriteback> findByAnalysisIdOrderByCreatedAtDesc(UUID analysisId);

	/** 이 분석에서 가장 마지막으로 적용된 수정본. 다음 수정은 이 위에 쌓는다. */
	Optional<WorkbookWriteback> findFirstByAnalysisIdAndStatusOrderByUpdatedAtDesc(
			UUID analysisId, WritebackStatus status);
}
