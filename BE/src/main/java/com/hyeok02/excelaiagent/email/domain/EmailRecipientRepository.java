package com.hyeok02.excelaiagent.email.domain;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

public interface EmailRecipientRepository extends JpaRepository<EmailRecipient, UUID> {

	List<EmailRecipient> findAllByOwnerUsernameAndActiveTrueOrderByCreatedAtDesc(
			String ownerUsername);

	List<EmailRecipient> findAllByOwnerUsernameAndRecipientIdInAndActiveTrue(
			String ownerUsername, Collection<UUID> recipientIds);

	Optional<EmailRecipient> findByOwnerUsernameAndRecipientIdAndActiveTrue(
			String ownerUsername, UUID recipientId);

	Optional<EmailRecipient> findByOwnerUsernameAndEmail(
			String ownerUsername, String email);
}
