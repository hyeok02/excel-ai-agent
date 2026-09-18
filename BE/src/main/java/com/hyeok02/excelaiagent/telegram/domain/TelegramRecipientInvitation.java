package com.hyeok02.excelaiagent.telegram.domain;

import java.time.Instant;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

@Entity
@Table(name = "telegram_recipient_invites")
public class TelegramRecipientInvitation {

	@Id
	@Column(name = "invite_id", nullable = false, updatable = false)
	private UUID invitationId;

	@Column(name = "owner_username", nullable = false, updatable = false, length = 100)
	private String ownerUsername;

	@Column(name = "label", length = 255)
	private String label;

	@Column(name = "token_hash", nullable = false, updatable = false, unique = true, length = 64)
	private String tokenHash;

	@ManyToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "recipient_id")
	private TelegramRecipient recipient;

	@Column(name = "created_at", nullable = false, updatable = false)
	private Instant createdAt;

	@Column(name = "expires_at", nullable = false, updatable = false)
	private Instant expiresAt;

	@Column(name = "consumed_at")
	private Instant consumedAt;

	@Column(name = "revoked_at")
	private Instant revokedAt;

	protected TelegramRecipientInvitation() {
	}

	private TelegramRecipientInvitation(
			UUID invitationId,
			String ownerUsername,
			String label,
			String tokenHash,
			Instant createdAt,
			Instant expiresAt) {
		this.invitationId = invitationId;
		this.ownerUsername = ownerUsername;
		this.label = label == null || label.isBlank() ? null : label.trim();
		this.tokenHash = tokenHash;
		this.createdAt = createdAt;
		this.expiresAt = expiresAt;
	}

	public static TelegramRecipientInvitation create(
			String ownerUsername,
			String label,
			String tokenHash,
			Instant now,
			Instant expiresAt) {
		return new TelegramRecipientInvitation(
				UUID.randomUUID(), ownerUsername, label, tokenHash, now, expiresAt);
	}

	public TelegramInvitationStatus status(Instant now) {
		if (revokedAt != null) {
			return TelegramInvitationStatus.REVOKED;
		}
		if (consumedAt != null) {
			return TelegramInvitationStatus.CONSUMED;
		}
		if (!expiresAt.isAfter(now)) {
			return TelegramInvitationStatus.EXPIRED;
		}
		return TelegramInvitationStatus.ACTIVE;
	}

	public boolean canConsume(Instant now) {
		return status(now) == TelegramInvitationStatus.ACTIVE;
	}

	public void consume(TelegramRecipient recipient, Instant now) {
		if (!canConsume(now)) {
			throw new IllegalStateException("사용할 수 없는 텔레그램 초대입니다.");
		}
		this.recipient = recipient;
		this.consumedAt = now;
	}

	public void revoke(Instant now) {
		if (status(now) != TelegramInvitationStatus.ACTIVE) {
			throw new IllegalStateException("활성 상태의 텔레그램 초대만 취소할 수 있습니다.");
		}
		this.revokedAt = now;
	}

	public UUID getInvitationId() {
		return invitationId;
	}

	public String getOwnerUsername() {
		return ownerUsername;
	}

	public String getLabel() {
		return label;
	}

	public Instant getCreatedAt() {
		return createdAt;
	}

	public Instant getExpiresAt() {
		return expiresAt;
	}
}
