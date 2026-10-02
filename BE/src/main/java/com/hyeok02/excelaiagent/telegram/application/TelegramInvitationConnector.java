package com.hyeok02.excelaiagent.telegram.application;

import java.time.Instant;

import com.hyeok02.excelaiagent.sharing.application.AnalysisPublicShareService;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipient;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientInvitation;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientInvitationRepository;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientRepository;
import com.hyeok02.excelaiagent.telegram.error.TelegramDeliveryException;
import com.hyeok02.excelaiagent.telegram.integration.TelegramClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * 초대 링크를 받은 사람을 수신자로 연결하고 결과를 알린다.
 *
 * 연결 절차는 수신자 목록 관리와 성격이 달라 따로 둔다. 트랜잭션 경계는
 * 호출하는 서비스가 쥔다.
 */
final class TelegramInvitationConnector {
	private static final Logger log =
			LoggerFactory.getLogger(TelegramInvitationConnector.class);

	private final TelegramRecipientRepository recipientRepository;
	private final TelegramRecipientInvitationRepository invitationRepository;
	private final TelegramClient telegramClient;
	private final AnalysisPublicShareService publicShareService;

	TelegramInvitationConnector(
			TelegramRecipientRepository recipientRepository,
			TelegramRecipientInvitationRepository invitationRepository,
			TelegramClient telegramClient,
			AnalysisPublicShareService publicShareService) {
		this.recipientRepository = recipientRepository;
		this.invitationRepository = invitationRepository;
		this.telegramClient = telegramClient;
		this.publicShareService = publicShareService;
	}

	TelegramRecipientConnection connect(
			String rawToken,
			String chatId,
			String telegramUserId,
			String telegramUsername,
			String firstName,
			String lastName) {
		Instant now = Instant.now();
		TelegramRecipientInvitation invitation = invitationRepository
				.findByTokenHash(TelegramInvitationTokens.hash(rawToken)).orElse(null);
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

	void sendConfirmation(TelegramRecipientConnection connection) {
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
}
