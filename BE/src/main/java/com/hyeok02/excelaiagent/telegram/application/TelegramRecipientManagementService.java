package com.hyeok02.excelaiagent.telegram.application;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.common.config.TelegramProperties;
import com.hyeok02.excelaiagent.sharing.application.AnalysisPublicShareService;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipient;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientInvitation;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientInvitationRepository;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientRepository;
import com.hyeok02.excelaiagent.telegram.error.InvalidTelegramInvitationException;
import com.hyeok02.excelaiagent.telegram.error.TelegramInvitationNotFoundException;
import com.hyeok02.excelaiagent.telegram.error.TelegramNotConfiguredException;
import com.hyeok02.excelaiagent.telegram.error.TelegramRecipientNotFoundException;
import com.hyeok02.excelaiagent.telegram.integration.TelegramClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TelegramRecipientManagementService {

	private final TelegramRecipientRepository recipientRepository;
	private final TelegramRecipientInvitationRepository invitationRepository;
	private final TelegramClient telegramClient;
	private final TelegramProperties properties;
	private final AnalysisPublicShareService publicShareService;
	private final TelegramInvitationConnector connector;

	public TelegramRecipientManagementService(
			TelegramRecipientRepository recipientRepository,
			TelegramRecipientInvitationRepository invitationRepository,
			TelegramClient telegramClient,
			TelegramProperties properties,
			AnalysisPublicShareService publicShareService) {
		this.recipientRepository = recipientRepository;
		this.invitationRepository = invitationRepository;
		this.telegramClient = telegramClient;
		this.properties = properties;
		this.publicShareService = publicShareService;
		this.connector = new TelegramInvitationConnector(
				recipientRepository, invitationRepository, telegramClient, publicShareService);
	}

	@Transactional
	public TelegramRecipientConnection connectFromInvitation(
			String rawToken,
			String chatId,
			String telegramUserId,
			String telegramUsername,
			String firstName,
			String lastName) {
		return connector.connect(
				rawToken, chatId, telegramUserId, telegramUsername, firstName, lastName);
	}

	public void sendConnectionConfirmation(TelegramRecipientConnection connection) {
		connector.sendConfirmation(connection);
	}

	@Transactional(readOnly = true)
	public List<TelegramRecipientView> listRecipients(String ownerUsername) {
		return recipientRepository
				.findAllByOwnerUsernameAndActiveTrueOrderByConnectedAtDesc(ownerUsername)
				.stream().map(TelegramRecipientView::from).toList();
	}

	@Transactional(readOnly = true)
	public List<TelegramInvitationView> listInvitations(String ownerUsername) {
		Instant now = Instant.now();
		return invitationRepository.findAllByOwnerUsernameOrderByCreatedAtDesc(ownerUsername)
				.stream().map(invitation -> TelegramInvitationView.from(invitation, now))
				.toList();
	}

	@Transactional
	public CreatedTelegramInvitation createInvitation(String ownerUsername, String label) {
		if (!properties.webhookConfigured()) {
			throw new TelegramNotConfiguredException();
		}
		String botUsername = telegramClient.getBotUsername();
		Instant now = Instant.now();
		String rawToken = TelegramInvitationTokens.issue();
		TelegramRecipientInvitation invitation = TelegramRecipientInvitation.create(
				ownerUsername, label, TelegramInvitationTokens.hash(rawToken), now, now.plus(properties.invitationTtl()));
		invitationRepository.save(invitation);
		return new CreatedTelegramInvitation(
				invitation.getInvitationId(), invitation.getLabel(),
				"https://t.me/%s?start=%s".formatted(botUsername, rawToken),
				invitation.getCreatedAt(), invitation.getExpiresAt(), "ACTIVE");
	}

	@Transactional
	public void revokeInvitation(String ownerUsername, UUID invitationId) {
		TelegramRecipientInvitation invitation = invitationRepository
				.findByOwnerUsernameAndInvitationId(ownerUsername, invitationId)
				.orElseThrow(TelegramInvitationNotFoundException::new);
		try {
			invitation.revoke(Instant.now());
		}
		catch (IllegalStateException exception) {
			throw new InvalidTelegramInvitationException();
		}
	}

	@Transactional
	public void deactivateRecipient(String ownerUsername, UUID recipientId) {
		TelegramRecipient recipient = recipientRepository
				.findByOwnerUsernameAndRecipientIdAndActiveTrue(ownerUsername, recipientId)
				.orElseThrow(TelegramRecipientNotFoundException::new);
		recipient.deactivate(Instant.now());
		publicShareService.revokeForRecipient(recipientId);
	}
}
