package com.hyeok02.excelaiagent.analysis.domain;

import java.util.List;
import java.util.UUID;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface WorkbookQuestionRepository extends JpaRepository<WorkbookQuestion, Long> {
	List<WorkbookQuestion> findByAnalysisIdOrderByIdDesc(UUID analysisId, Pageable page);

	List<WorkbookQuestion> findByAnalysisIdAndIdLessThanOrderByIdDesc(
			UUID analysisId, Long before, Pageable page);
}
