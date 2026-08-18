package com.hyeok02.excelaiagent.analysis.domain;

import java.time.Instant;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Lob;
import jakarta.persistence.Table;

@Entity
@Table(name = "analysis_results")
public class AnalysisResult {

	@Id
	@Column(name = "analysis_id", nullable = false, updatable = false)
	private UUID analysisId;

	@Lob
	@Column(name = "result_json", nullable = false)
	private String resultJson;

	@Column(name = "created_at", nullable = false, updatable = false)
	private Instant createdAt;

	protected AnalysisResult() {
	}

	private AnalysisResult(UUID analysisId, String resultJson, Instant createdAt) {
		this.analysisId = analysisId;
		this.resultJson = resultJson;
		this.createdAt = createdAt;
	}

	public static AnalysisResult completed(UUID analysisId, String resultJson, Instant createdAt) {
		return new AnalysisResult(analysisId, resultJson, createdAt);
	}

	public UUID getAnalysisId() {
		return analysisId;
	}

	public String getResultJson() {
		return resultJson;
	}

	public Instant getCreatedAt() {
		return createdAt;
	}
}
