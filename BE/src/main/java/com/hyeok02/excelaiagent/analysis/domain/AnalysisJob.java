package com.hyeok02.excelaiagent.analysis.domain;

import java.time.Instant;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "analysis_jobs")
public class AnalysisJob {

	@Id
	@Column(name = "analysis_id", nullable = false, updatable = false)
	private UUID analysisId;

	@Enumerated(EnumType.STRING)
	@Column(name = "status", nullable = false, length = 20)
	private AnalysisStatus status;

	@Enumerated(EnumType.STRING)
	@Column(name = "analysis_mode", nullable = false, length = 20)
	private AnalysisMode mode;

	@Column(name = "original_filename", nullable = false, length = 255)
	private String originalFilename;

	@Column(name = "file_extension", nullable = false, length = 10)
	private String fileExtension;

	@Column(name = "file_size_bytes", nullable = false)
	private long fileSizeBytes;

	@Column(name = "owner_username", length = 100)
	private String ownerUsername;

	@Column(name = "failure_message", length = 500)
	private String failureMessage;

	@Column(name = "created_at", nullable = false, updatable = false)
	private Instant createdAt;

	@Column(name = "updated_at", nullable = false)
	private Instant updatedAt;

	protected AnalysisJob() {
	}

	private AnalysisJob(
			UUID analysisId,
			AnalysisMode mode,
			String originalFilename,
			String fileExtension,
			long fileSizeBytes,
			String ownerUsername,
			Instant now) {
		this.analysisId = analysisId;
		this.status = AnalysisStatus.QUEUED;
		this.mode = mode;
		this.originalFilename = originalFilename;
		this.fileExtension = fileExtension;
		this.fileSizeBytes = fileSizeBytes;
		this.ownerUsername = ownerUsername;
		this.createdAt = now;
		this.updatedAt = now;
	}

	public static AnalysisJob queued(
			UUID analysisId,
			AnalysisMode mode,
			String originalFilename,
			String fileExtension,
			long fileSizeBytes,
			String ownerUsername,
			Instant now) {
		return new AnalysisJob(analysisId, mode, originalFilename, fileExtension,
				fileSizeBytes, ownerUsername, now);
	}

	public void markProcessing(Instant now) {
		transitionFrom(AnalysisStatus.QUEUED, AnalysisStatus.PROCESSING, now);
	}

	public void markCompleted(Instant now) {
		transitionFrom(AnalysisStatus.PROCESSING, AnalysisStatus.COMPLETED, now);
	}

	public void markFailed(Instant now) {
		markFailed(now, null);
	}

	public void markFailed(Instant now, String failureMessage) {
		transitionFrom(AnalysisStatus.PROCESSING, AnalysisStatus.FAILED, now);
		this.failureMessage = failureMessage;
	}

	private void transitionFrom(AnalysisStatus expected, AnalysisStatus next, Instant now) {
		if (status != expected) {
			throw new IllegalStateException(
					"분석 상태를 %s에서 %s로 변경할 수 없습니다.".formatted(status, next));
		}
		status = next;
		updatedAt = now;
	}

	public UUID getAnalysisId() {
		return analysisId;
	}

	public AnalysisStatus getStatus() {
		return status;
	}

	public AnalysisMode getMode() {
		return mode;
	}

	public String getOriginalFilename() {
		return originalFilename;
	}

	public String getFileExtension() {
		return fileExtension;
	}

	public long getFileSizeBytes() {
		return fileSizeBytes;
	}

	public String getOwnerUsername() {
		return ownerUsername;
	}

	public String getFailureMessage() {
		return failureMessage;
	}

	public Instant getCreatedAt() {
		return createdAt;
	}

	public Instant getUpdatedAt() {
		return updatedAt;
	}
}
