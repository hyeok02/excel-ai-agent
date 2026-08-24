package com.hyeok02.excelaiagent.auth.domain;

import java.time.Instant;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "app_users")
public class AppUser {

	@Id
	@Column(name = "user_id", nullable = false, updatable = false)
	private UUID userId;

	@Column(name = "username", nullable = false, unique = true, length = 100)
	private String username;

	@Column(name = "password_hash", length = 100)
	private String passwordHash;

	@Column(name = "display_name", nullable = false, length = 100)
	private String displayName;

	@Column(name = "email", unique = true, length = 255)
	private String email;

	@Enumerated(EnumType.STRING)
	@Column(name = "user_role", nullable = false, length = 20)
	private UserRole role;

	@Enumerated(EnumType.STRING)
	@Column(name = "auth_provider", nullable = false, length = 20)
	private AuthProvider authProvider;

	@Column(name = "enabled", nullable = false)
	private boolean enabled;

	@Column(name = "created_at", nullable = false, updatable = false)
	private Instant createdAt;

	@Column(name = "updated_at", nullable = false)
	private Instant updatedAt;

	protected AppUser() {
	}

	private AppUser(
			UUID userId,
			String username,
			String passwordHash,
			String displayName,
			String email,
			UserRole role,
			AuthProvider authProvider,
			boolean enabled,
			Instant createdAt,
			Instant updatedAt) {
		this.userId = userId;
		this.username = username;
		this.passwordHash = passwordHash;
		this.displayName = displayName;
		this.email = email;
		this.role = role;
		this.authProvider = authProvider;
		this.enabled = enabled;
		this.createdAt = createdAt;
		this.updatedAt = updatedAt;
	}

	public static AppUser local(
			String username,
			String passwordHash,
			String displayName,
			UserRole role,
			Instant now) {
		return new AppUser(
				UUID.randomUUID(), username, passwordHash, displayName, null,
				role, AuthProvider.LOCAL, true, now, now);
	}

	public static AppUser sso(
			String username,
			String displayName,
			String email,
			Instant now) {
		return new AppUser(
				UUID.randomUUID(), username, null, displayName, email,
				UserRole.USER, AuthProvider.SSO, true, now, now);
	}

	public void updateSsoProfile(String displayName, Instant now) {
		this.displayName = displayName;
		this.updatedAt = now;
	}

	public UUID getUserId() {
		return userId;
	}

	public String getUsername() {
		return username;
	}

	public String getPasswordHash() {
		return passwordHash;
	}

	public String getDisplayName() {
		return displayName;
	}

	public String getEmail() {
		return email;
	}

	public UserRole getRole() {
		return role;
	}

	public AuthProvider getAuthProvider() {
		return authProvider;
	}

	public boolean isEnabled() {
		return enabled;
	}

	public Instant getCreatedAt() {
		return createdAt;
	}

	public Instant getUpdatedAt() {
		return updatedAt;
	}
}
