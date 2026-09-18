package com.hyeok02.excelaiagent.sharing.domain;

import java.time.Instant;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "analysis_public_shares")
public class AnalysisPublicShare {

	@Id
	@Column(name = "share_id", nullable = false, updatable = false)
	private UUID shareId;

	@Column(name = "analysis_id", nullable = false, updatable = false)
	private UUID analysisId;

	@Column(name = "recipient_id", nullable = false, updatable = false)
	private UUID recipientId;

	@Column(name = "token_hash", nullable = false, updatable = false, unique = true, length = 64)
	private String tokenHash;

	@Column(name = "created_at", nullable = false, updatable = false)
	private Instant createdAt;

	@Column(name = "expires_at", nullable = false, updatable = false)
	private Instant expiresAt;

	@Column(name = "revoked_at")
	private Instant revokedAt;

	protected AnalysisPublicShare() {
	}

	private AnalysisPublicShare(
			UUID shareId,
			UUID analysisId,
			UUID recipientId,
			String tokenHash,
			Instant createdAt,
			Instant expiresAt) {
		this.shareId = shareId;
		this.analysisId = analysisId;
		this.recipientId = recipientId;
		this.tokenHash = tokenHash;
		this.createdAt = createdAt;
		this.expiresAt = expiresAt;
	}

	public static AnalysisPublicShare issue(
			UUID analysisId,
			UUID recipientId,
			String tokenHash,
			Instant createdAt,
			Instant expiresAt) {
		return new AnalysisPublicShare(
				UUID.randomUUID(), analysisId, recipientId, tokenHash, createdAt, expiresAt);
	}

	public boolean isAccessibleAt(Instant now) {
		return revokedAt == null && expiresAt.isAfter(now);
	}

	public void revoke(Instant now) {
		if (revokedAt == null) {
			revokedAt = now;
		}
	}

	public UUID getShareId() {
		return shareId;
	}

	public UUID getAnalysisId() {
		return analysisId;
	}

	public UUID getRecipientId() {
		return recipientId;
	}

	public String getTokenHash() {
		return tokenHash;
	}

	public Instant getCreatedAt() {
		return createdAt;
	}

	public Instant getExpiresAt() {
		return expiresAt;
	}

	public Instant getRevokedAt() {
		return revokedAt;
	}
}
