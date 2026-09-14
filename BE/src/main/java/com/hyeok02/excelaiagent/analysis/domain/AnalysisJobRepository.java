package com.hyeok02.excelaiagent.analysis.domain;

import java.time.Instant;
import java.util.Collection;
import java.util.List;
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

	@Modifying
	@Query("update AnalysisJob job set job.status = :nextStatus, "
			+ "job.failureMessage = :failureMessage, job.updatedAt = :now "
			+ "where job.status in :currentStatuses")
	int updateStatusOfJobsIn(
			@Param("currentStatuses") Collection<AnalysisStatus> currentStatuses,
			@Param("nextStatus") AnalysisStatus nextStatus,
			@Param("failureMessage") String failureMessage,
			@Param("now") Instant now);

	/**
	 * 서버가 내려가 중단된 작업을 실패로 정리한다.
	 * 접수(QUEUED)·처리(PROCESSING) 중이던 작업만 대상이며, 이미 끝난 작업은 건드리지 않는다.
	 */
	default int failInterruptedJobs(String failureMessage, Instant now) {
		return updateStatusOfJobsIn(
				List.of(AnalysisStatus.QUEUED, AnalysisStatus.PROCESSING),
				AnalysisStatus.FAILED, failureMessage, now);
	}
}
