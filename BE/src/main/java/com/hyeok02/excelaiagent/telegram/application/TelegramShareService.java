package com.hyeok02.excelaiagent.telegram.application;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

import com.hyeok02.excelaiagent.analysis.application.AnalysisResultDetails;
import com.hyeok02.excelaiagent.analysis.application.AnalysisResultReader;
import com.hyeok02.excelaiagent.common.config.AuthProperties;
import com.hyeok02.excelaiagent.sharing.application.AnalysisPublicShareService;
import com.hyeok02.excelaiagent.sharing.application.IssuedAnalysisPublicShare;
import com.hyeok02.excelaiagent.telegram.api.TelegramShareResponse;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipient;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientRepository;
import com.hyeok02.excelaiagent.telegram.error.InvalidTelegramShareRequestException;
import com.hyeok02.excelaiagent.telegram.error.TelegramDeliveryException;
import com.hyeok02.excelaiagent.telegram.error.TelegramRecipientNotFoundException;
import com.hyeok02.excelaiagent.telegram.integration.TelegramClient;
import org.springframework.stereotype.Service;

@Service
public class TelegramShareService {
	private static final int MAX_RECIPIENTS_PER_SHARE = 50;

	private final AnalysisResultReader resultReader;
	private final TelegramMessageFormatter messageFormatter;
	private final TelegramClient telegramClient;
	private final TelegramRecipientRepository recipientRepository;
	private final AnalysisPublicShareService publicShareService;
	private final AuthProperties authProperties;

	public TelegramShareService(
			AnalysisResultReader resultReader,
			TelegramMessageFormatter messageFormatter,
			TelegramClient telegramClient,
			TelegramRecipientRepository recipientRepository,
			AnalysisPublicShareService publicShareService,
			AuthProperties authProperties) {
		this.resultReader = resultReader;
		this.messageFormatter = messageFormatter;
		this.telegramClient = telegramClient;
		this.recipientRepository = recipientRepository;
		this.publicShareService = publicShareService;
		this.authProperties = authProperties;
	}

	public TelegramShareResponse share(
			UUID analysisId, String ownerUsername, List<UUID> selectedRecipientIds) {
		AnalysisResultDetails result = resultReader.getResult(analysisId, ownerUsername);
		Instant sentAt = Instant.now();
		if (selectedRecipientIds == null) {
			telegramClient.sendMessage(messageFormatter.format(result));
			return TelegramShareResponse.legacy(sentAt);
		}
		if (selectedRecipientIds.size() > MAX_RECIPIENTS_PER_SHARE) {
			throw new InvalidTelegramShareRequestException(
					"텔레그램 수신자는 한 번에 최대 50명까지 선택할 수 있습니다.");
		}

		LinkedHashSet<UUID> requestedIds = new LinkedHashSet<>(selectedRecipientIds);
		if (requestedIds.isEmpty() || requestedIds.contains(null)) {
			throw new InvalidTelegramShareRequestException();
		}
		List<TelegramRecipient> found = recipientRepository
				.findAllByOwnerUsernameAndRecipientIdInAndActiveTrue(ownerUsername, requestedIds);
		if (found.size() != requestedIds.size()) {
			throw new TelegramRecipientNotFoundException();
		}
		Map<UUID, TelegramRecipient> byId = found.stream().collect(Collectors.toMap(
				TelegramRecipient::getRecipientId, Function.identity()));
		List<TelegramShareResponse.Delivery> deliveries = new ArrayList<>();
		for (UUID recipientId : requestedIds) {
			TelegramRecipient recipient = byId.get(recipientId);
			IssuedAnalysisPublicShare publicShare = publicShareService.issue(
					analysisId, recipientId, ownerUsername);
			String detailsUrl = authProperties.frontendBaseUrl()
					+ "/shared/analysis/" + publicShare.token();
			try {
				telegramClient.sendMessage(
						recipient.getChatId(), messageFormatter.format(result, detailsUrl));
				deliveries.add(new TelegramShareResponse.Delivery(
						recipientId, recipient.getDisplayName(), true, null));
			}
			catch (TelegramDeliveryException exception) {
				publicShareService.revoke(publicShare.shareId());
				deliveries.add(new TelegramShareResponse.Delivery(
						recipientId, recipient.getDisplayName(), false,
						"텔레그램 메시지를 전송하지 못했습니다."));
			}
			catch (RuntimeException exception) {
				// A link that never reached its recipient must not remain usable.
				publicShareService.revoke(publicShare.shareId());
				throw exception;
			}
		}
		return TelegramShareResponse.of(sentAt, deliveries);
	}
}
