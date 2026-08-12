package com.hyeok02.excelaiagent.analysis.domain;

import java.util.UUID;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AnalysisJobRepository extends JpaRepository<AnalysisJob, UUID> {

	Page<AnalysisJob> findByMode(AnalysisMode mode, Pageable pageable);

	Page<AnalysisJob> findByOriginalFilenameContainingIgnoreCase(String filename, Pageable pageable);

	Page<AnalysisJob> findByModeAndOriginalFilenameContainingIgnoreCase(
			AnalysisMode mode,
			String filename,
			Pageable pageable);
}
