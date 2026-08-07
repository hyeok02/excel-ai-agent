package com.hyeok02.excelaiagent.analysis.domain;

import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

public interface AnalysisJobRepository extends JpaRepository<AnalysisJob, UUID> {
}
