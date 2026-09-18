package com.hyeok02.excelaiagent.telegram.domain;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;

public interface TelegramRecipientInvitationRepository
		extends JpaRepository<TelegramRecipientInvitation, UUID> {

	List<TelegramRecipientInvitation> findAllByOwnerUsernameOrderByCreatedAtDesc(
			String ownerUsername);

	Optional<TelegramRecipientInvitation> findByOwnerUsernameAndInvitationId(
			String ownerUsername, UUID invitationId);

	@Lock(LockModeType.PESSIMISTIC_WRITE)
	Optional<TelegramRecipientInvitation> findByTokenHash(String tokenHash);
}
