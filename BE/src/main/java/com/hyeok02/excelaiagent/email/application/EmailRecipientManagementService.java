package com.hyeok02.excelaiagent.email.application;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.email.domain.EmailRecipient;
import com.hyeok02.excelaiagent.email.domain.EmailRecipientRepository;
import com.hyeok02.excelaiagent.email.error.DuplicateEmailRecipientException;
import com.hyeok02.excelaiagent.email.error.EmailRecipientNotFoundException;
import com.hyeok02.excelaiagent.sharing.application.AnalysisPublicShareService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class EmailRecipientManagementService {
	private final EmailRecipientRepository recipientRepository;
	private final AnalysisPublicShareService publicShareService;

	public EmailRecipientManagementService(
			EmailRecipientRepository recipientRepository,
			AnalysisPublicShareService publicShareService) {
		this.recipientRepository = recipientRepository;
		this.publicShareService = publicShareService;
	}

	@Transactional(readOnly = true)
	public List<EmailRecipientView> listRecipients(String ownerUsername) {
		return recipientRepository
				.findAllByOwnerUsernameAndActiveTrueOrderByCreatedAtDesc(ownerUsername)
				.stream().map(EmailRecipientView::from).toList();
	}

	@Transactional
	public EmailRecipientView registerRecipient(
			String ownerUsername, String email, String displayName) {
		String normalizedEmail = EmailRecipient.normalizeEmail(email);
		Instant now = Instant.now();
		EmailRecipient recipient = recipientRepository
				.findByOwnerUsernameAndEmail(ownerUsername, normalizedEmail)
				.orElse(null);
		if (recipient == null) {
			recipient = EmailRecipient.registered(
					ownerUsername, normalizedEmail, displayName, now);
		}
		else if (recipient.isActive()) {
			throw new DuplicateEmailRecipientException();
		}
		else {
			recipient.reactivate(displayName, now);
		}
		return EmailRecipientView.from(recipientRepository.save(recipient));
	}

	@Transactional
	public void deactivateRecipient(String ownerUsername, UUID recipientId) {
		EmailRecipient recipient = recipientRepository
				.findByOwnerUsernameAndRecipientIdAndActiveTrue(ownerUsername, recipientId)
				.orElseThrow(EmailRecipientNotFoundException::new);
		recipient.deactivate(Instant.now());
		publicShareService.revokeForEmailRecipient(recipientId);
	}
}
