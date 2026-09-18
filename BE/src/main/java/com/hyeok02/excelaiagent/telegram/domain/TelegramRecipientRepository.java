package com.hyeok02.excelaiagent.telegram.domain;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

public interface TelegramRecipientRepository extends JpaRepository<TelegramRecipient, UUID> {

	List<TelegramRecipient> findAllByOwnerUsernameAndActiveTrueOrderByConnectedAtDesc(
			String ownerUsername);

	List<TelegramRecipient> findAllByOwnerUsernameAndRecipientIdInAndActiveTrue(
			String ownerUsername, Collection<UUID> recipientIds);

	Optional<TelegramRecipient> findByOwnerUsernameAndRecipientIdAndActiveTrue(
			String ownerUsername, UUID recipientId);

	Optional<TelegramRecipient> findByOwnerUsernameAndChatId(
			String ownerUsername, String chatId);
}
