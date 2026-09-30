package com.hyeok02.excelaiagent.email.application;

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
import com.hyeok02.excelaiagent.email.api.EmailShareResponse;
import com.hyeok02.excelaiagent.email.domain.EmailRecipient;
import com.hyeok02.excelaiagent.email.domain.EmailRecipientRepository;
import com.hyeok02.excelaiagent.email.error.EmailDeliveryException;
import com.hyeok02.excelaiagent.email.error.EmailRecipientNotFoundException;
import com.hyeok02.excelaiagent.email.error.InvalidEmailShareRequestException;
import com.hyeok02.excelaiagent.email.integration.EmailClient;
import com.hyeok02.excelaiagent.sharing.application.AnalysisPublicShareService;
import com.hyeok02.excelaiagent.sharing.application.IssuedAnalysisPublicShare;
import org.springframework.stereotype.Service;

@Service
public class EmailShareService {
	private static final int MAX_RECIPIENTS_PER_SHARE = 50;

	private final AnalysisResultReader resultReader;
	private final EmailMessageFormatter messageFormatter;
	private final EmailClient emailClient;
	private final EmailRecipientRepository recipientRepository;
	private final AnalysisPublicShareService publicShareService;
	private final AuthProperties authProperties;

	public EmailShareService(
			AnalysisResultReader resultReader,
			EmailMessageFormatter messageFormatter,
			EmailClient emailClient,
			EmailRecipientRepository recipientRepository,
			AnalysisPublicShareService publicShareService,
			AuthProperties authProperties) {
		this.resultReader = resultReader;
		this.messageFormatter = messageFormatter;
		this.emailClient = emailClient;
		this.recipientRepository = recipientRepository;
		this.publicShareService = publicShareService;
		this.authProperties = authProperties;
	}

	public EmailShareResponse share(
			UUID analysisId, String ownerUsername, List<UUID> selectedRecipientIds) {
		AnalysisResultDetails result = resultReader.getResult(analysisId, ownerUsername);
		if (selectedRecipientIds == null || selectedRecipientIds.isEmpty()
				|| selectedRecipientIds.contains(null)) {
			throw new InvalidEmailShareRequestException();
		}
		if (selectedRecipientIds.size() > MAX_RECIPIENTS_PER_SHARE) {
			throw new InvalidEmailShareRequestException(
					"이메일 수신자는 한 번에 최대 50명까지 선택할 수 있습니다.");
		}

		LinkedHashSet<UUID> requestedIds = new LinkedHashSet<>(selectedRecipientIds);
		List<EmailRecipient> found = recipientRepository
				.findAllByOwnerUsernameAndRecipientIdInAndActiveTrue(ownerUsername, requestedIds);
		if (found.size() != requestedIds.size()) {
			throw new EmailRecipientNotFoundException();
		}
		Map<UUID, EmailRecipient> byId = found.stream().collect(Collectors.toMap(
				EmailRecipient::getRecipientId, Function.identity()));

		Instant sentAt = Instant.now();
		List<EmailShareResponse.Delivery> deliveries = new ArrayList<>();
		for (UUID recipientId : requestedIds) {
			EmailRecipient recipient = byId.get(recipientId);
			IssuedAnalysisPublicShare publicShare = publicShareService.issueForEmail(
					analysisId, recipientId, ownerUsername);
			String detailsUrl = authProperties.frontendBaseUrl()
					+ "/shared/analysis/" + publicShare.token();
			try {
				FormattedEmail email = messageFormatter.format(result, detailsUrl);
				emailClient.send(
						recipient.getEmail(),
						email.subject(),
						email.plainTextBody(),
						email.htmlBody());
				deliveries.add(new EmailShareResponse.Delivery(
						recipientId, recipient.getDisplayName(), true, null));
			}
			catch (EmailDeliveryException exception) {
				publicShareService.revoke(publicShare.shareId());
				deliveries.add(new EmailShareResponse.Delivery(
						recipientId, recipient.getDisplayName(), false,
						"이메일을 전송하지 못했습니다."));
			}
			catch (RuntimeException exception) {
				publicShareService.revoke(publicShare.shareId());
				throw exception;
			}
		}
		return EmailShareResponse.of(sentAt, deliveries);
	}
}
