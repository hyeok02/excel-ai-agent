package com.hyeok02.excelaiagent.writeback.domain;

import java.util.List;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

public interface WorkbookWritebackRepository extends JpaRepository<WorkbookWriteback, UUID> {
	List<WorkbookWriteback> findByAnalysisIdOrderByCreatedAtDesc(UUID analysisId);
}
