package com.hyeok02.excelaiagent.email.domain;

import java.time.Instant;
import java.util.Locale;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "email_recipients")
public class EmailRecipient {

	@Id
	@Column(name = "recipient_id", nullable = false, updatable = false)
	private UUID recipientId;

	@Column(name = "owner_username", nullable = false, updatable = false, length = 100)
	private String ownerUsername;

	@Column(name = "email", nullable = false, updatable = false, length = 255)
	private String email;

	@Column(name = "display_name", nullable = false, length = 255)
	private String displayName;

	@Column(name = "active", nullable = false)
	private boolean active;

	@Column(name = "created_at", nullable = false, updatable = false)
	private Instant createdAt;

	@Column(name = "updated_at", nullable = false)
	private Instant updatedAt;

	protected EmailRecipient() {
	}

	private EmailRecipient(
			UUID recipientId,
			String ownerUsername,
			String email,
			String displayName,
			Instant now) {
		this.recipientId = recipientId;
		this.ownerUsername = ownerUsername;
		this.email = normalizeEmail(email);
		this.displayName = displayName(displayName, this.email);
		this.active = true;
		this.createdAt = now;
		this.updatedAt = now;
	}

	public static EmailRecipient registered(
			String ownerUsername, String email, String displayName, Instant now) {
		return new EmailRecipient(
				UUID.randomUUID(), ownerUsername, email, displayName, now);
	}

	public void reactivate(String displayName, Instant now) {
		this.displayName = displayName(displayName, email);
		this.active = true;
		this.updatedAt = now;
	}

	public void deactivate(Instant now) {
		this.active = false;
		this.updatedAt = now;
	}

	public static String normalizeEmail(String email) {
		return email == null ? "" : email.trim().toLowerCase(Locale.ROOT);
	}

	private static String displayName(String displayName, String email) {
		return displayName == null || displayName.isBlank()
				? email
				: displayName.trim();
	}

	public UUID getRecipientId() {
		return recipientId;
	}

	public String getOwnerUsername() {
		return ownerUsername;
	}

	public String getEmail() {
		return email;
	}

	public String getDisplayName() {
		return displayName;
	}

	public boolean isActive() {
		return active;
	}

	public Instant getCreatedAt() {
		return createdAt;
	}
}
