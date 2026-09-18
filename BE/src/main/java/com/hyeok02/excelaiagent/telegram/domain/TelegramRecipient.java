package com.hyeok02.excelaiagent.telegram.domain;

import java.time.Instant;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "telegram_recipients")
public class TelegramRecipient {

	@Id
	@Column(name = "recipient_id", nullable = false, updatable = false)
	private UUID recipientId;

	@Column(name = "owner_username", nullable = false, updatable = false, length = 100)
	private String ownerUsername;

	@Column(name = "chat_id", nullable = false, updatable = false, length = 32)
	private String chatId;

	@Column(name = "telegram_user_id", nullable = false, length = 32)
	private String telegramUserId;

	@Column(name = "telegram_username", length = 255)
	private String telegramUsername;

	@Column(name = "first_name", length = 255)
	private String firstName;

	@Column(name = "last_name", length = 255)
	private String lastName;

	@Column(name = "display_name", nullable = false, length = 255)
	private String displayName;

	@Column(name = "active", nullable = false)
	private boolean active;

	@Column(name = "connected_at", nullable = false, updatable = false)
	private Instant connectedAt;

	@Column(name = "updated_at", nullable = false)
	private Instant updatedAt;

	protected TelegramRecipient() {
	}

	private TelegramRecipient(
			UUID recipientId,
			String ownerUsername,
			String chatId,
			String telegramUserId,
			String telegramUsername,
			String firstName,
			String lastName,
			String displayName,
			Instant now) {
		this.recipientId = recipientId;
		this.ownerUsername = ownerUsername;
		this.chatId = chatId;
		this.telegramUserId = telegramUserId;
		this.telegramUsername = telegramUsername;
		this.firstName = firstName;
		this.lastName = lastName;
		this.displayName = displayName;
		this.active = true;
		this.connectedAt = now;
		this.updatedAt = now;
	}

	public static TelegramRecipient connected(
			String ownerUsername,
			String chatId,
			String telegramUserId,
			String telegramUsername,
			String firstName,
			String lastName,
			String invitationLabel,
			Instant now) {
		return new TelegramRecipient(
				UUID.randomUUID(), ownerUsername, chatId, telegramUserId,
				normalize(telegramUsername), normalize(firstName), normalize(lastName),
				displayName(invitationLabel, telegramUsername, firstName, lastName), now);
	}

	public void reconnect(
			String telegramUserId,
			String telegramUsername,
			String firstName,
			String lastName,
			String invitationLabel,
			Instant now) {
		this.telegramUserId = telegramUserId;
		this.telegramUsername = normalize(telegramUsername);
		this.firstName = normalize(firstName);
		this.lastName = normalize(lastName);
		this.displayName = displayName(invitationLabel, telegramUsername, firstName, lastName);
		this.active = true;
		this.updatedAt = now;
	}

	public void deactivate(Instant now) {
		this.active = false;
		this.updatedAt = now;
	}

	private static String displayName(
			String invitationLabel, String username, String firstName, String lastName) {
		String label = normalize(invitationLabel);
		if (label != null) {
			return label;
		}
		String fullName = ((normalize(firstName) == null ? "" : firstName.trim()) + " "
				+ (normalize(lastName) == null ? "" : lastName.trim())).trim();
		if (!fullName.isBlank()) {
			return fullName;
		}
		String normalizedUsername = normalize(username);
		return normalizedUsername == null ? "Telegram 사용자" : "@" + normalizedUsername;
	}

	private static String normalize(String value) {
		return value == null || value.isBlank() ? null : value.trim();
	}

	public UUID getRecipientId() {
		return recipientId;
	}

	public String getOwnerUsername() {
		return ownerUsername;
	}

	public String getChatId() {
		return chatId;
	}

	public String getTelegramUserId() {
		return telegramUserId;
	}

	public String getTelegramUsername() {
		return telegramUsername;
	}

	public String getDisplayName() {
		return displayName;
	}

	public boolean isActive() {
		return active;
	}

	public Instant getConnectedAt() {
		return connectedAt;
	}
}
