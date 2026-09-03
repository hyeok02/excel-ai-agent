package com.hyeok02.excelaiagent.analysis.domain;

import java.util.Optional;
import java.util.UUID;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AnalysisJobRepository extends JpaRepository<AnalysisJob, UUID> {

	Optional<AnalysisJob> findByAnalysisIdAndOwnerUsername(UUID analysisId, String ownerUsername);

	Page<AnalysisJob> findByOwnerUsername(String ownerUsername, Pageable pageable);

	Page<AnalysisJob> findByOwnerUsernameAndMode(
			String ownerUsername, AnalysisMode mode, Pageable pageable);

	Page<AnalysisJob> findByOwnerUsernameAndOriginalFilenameContainingIgnoreCase(
			String ownerUsername, String filename, Pageable pageable);

	Page<AnalysisJob> findByOwnerUsernameAndModeAndOriginalFilenameContainingIgnoreCase(
			String ownerUsername,
			AnalysisMode mode,
			String filename,
			Pageable pageable);

	@Modifying
	@Query("update AnalysisJob job set job.ownerUsername = :ownerUsername "
			+ "where job.ownerUsername is null")
	int assignUnownedTo(@Param("ownerUsername") String ownerUsername);
}
