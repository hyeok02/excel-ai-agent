package com.hyeok02.excelaiagent.telegram.application;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.common.config.TelegramProperties;
import com.hyeok02.excelaiagent.sharing.application.AnalysisPublicShareService;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipient;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientInvitation;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientInvitationRepository;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientRepository;
import com.hyeok02.excelaiagent.telegram.error.InvalidTelegramInvitationException;
import com.hyeok02.excelaiagent.telegram.error.TelegramDeliveryException;
import com.hyeok02.excelaiagent.telegram.error.TelegramInvitationNotFoundException;
import com.hyeok02.excelaiagent.telegram.error.TelegramNotConfiguredException;
import com.hyeok02.excelaiagent.telegram.error.TelegramRecipientNotFoundException;
import com.hyeok02.excelaiagent.telegram.integration.TelegramClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TelegramRecipientManagementService {
	private static final Logger log =
			LoggerFactory.getLogger(TelegramRecipientManagementService.class);
	private static final SecureRandom SECURE_RANDOM = new SecureRandom();

	private final TelegramRecipientRepository recipientRepository;
	private final TelegramRecipientInvitationRepository invitationRepository;
	private final TelegramClient telegramClient;
	private final TelegramProperties properties;
	private final AnalysisPublicShareService publicShareService;

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
		String rawToken = token();
		TelegramRecipientInvitation invitation = TelegramRecipientInvitation.create(
				ownerUsername, label, hash(rawToken), now, now.plus(properties.invitationTtl()));
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

	@Transactional
	public TelegramRecipientConnection connectFromInvitation(
			String rawToken,
			String chatId,
			String telegramUserId,
			String telegramUsername,
			String firstName,
			String lastName) {
		Instant now = Instant.now();
		TelegramRecipientInvitation invitation = invitationRepository
				.findByTokenHash(hash(rawToken)).orElse(null);
		if (invitation == null || !invitation.canConsume(now)) {
			return new TelegramRecipientConnection(
					chatId, null,
					TelegramRecipientConnection.ConnectionStatus.INVALID_INVITATION);
		}

		TelegramRecipient recipient = recipientRepository
				.findByOwnerUsernameAndChatId(invitation.getOwnerUsername(), chatId)
				.orElse(null);
		if (recipient == null) {
			recipient = TelegramRecipient.connected(
					invitation.getOwnerUsername(), chatId, telegramUserId,
					telegramUsername, firstName, lastName, invitation.getLabel(), now);
		}
		else {
			if (!recipient.isActive()) {
				// Also closes the narrow deactivate/reconnect race so an older bearer link
				// cannot become usable again when the same chat is reconnected.
				publicShareService.revokeForRecipient(recipient.getRecipientId());
			}
			recipient.reconnect(
					telegramUserId, telegramUsername, firstName, lastName,
					invitation.getLabel(), now);
		}
		recipient = recipientRepository.save(recipient);
		invitation.consume(recipient, now);
		return new TelegramRecipientConnection(
				chatId, recipient.getDisplayName(),
				TelegramRecipientConnection.ConnectionStatus.CONNECTED);
	}

	public void sendConnectionConfirmation(TelegramRecipientConnection connection) {
		String text = connection.status()
				== TelegramRecipientConnection.ConnectionStatus.CONNECTED
				? "✅ %s님이 Excel AI Agent 텔레그램 수신자로 연결되었습니다."
						.formatted(connection.displayName())
				: "⚠️ 이 초대 링크는 만료되었거나 이미 사용되었습니다. 새 링크를 요청해주세요.";
		try {
			telegramClient.sendMessage(connection.chatId(), text);
		}
		catch (TelegramDeliveryException exception) {
			// The wrapped HTTP exception may include the bot token in its request URL.
			log.warn("Telegram recipient confirmation could not be delivered");
		}
	}

	private String token() {
		byte[] bytes = new byte[32];
		SECURE_RANDOM.nextBytes(bytes);
		return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
	}

	private String hash(String rawToken) {
		if (rawToken == null || rawToken.isBlank()) {
			throw new InvalidTelegramInvitationException();
		}
		try {
			return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
					.digest(rawToken.getBytes(StandardCharsets.UTF_8)));
		}
		catch (NoSuchAlgorithmException exception) {
			throw new IllegalStateException("SHA-256 is not available", exception);
		}
	}
}
