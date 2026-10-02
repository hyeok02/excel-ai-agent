package com.hyeok02.excelaiagent.sharing.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.application.AnalysisAccessService;
import com.hyeok02.excelaiagent.analysis.application.AnalysisResultDetails;
import com.hyeok02.excelaiagent.analysis.application.AnalysisResultReader;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResultRepository;
import com.hyeok02.excelaiagent.analysis.error.AnalysisResultNotReadyException;
import com.hyeok02.excelaiagent.common.config.AnalysisPublicShareProperties;
import com.hyeok02.excelaiagent.email.domain.EmailRecipient;
import com.hyeok02.excelaiagent.email.domain.EmailRecipientRepository;
import com.hyeok02.excelaiagent.sharing.domain.AnalysisPublicShare;
import com.hyeok02.excelaiagent.sharing.domain.AnalysisPublicShareRepository;
import com.hyeok02.excelaiagent.sharing.error.AnalysisPublicShareNotFoundException;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipient;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AnalysisPublicShareService {

	private final AnalysisPublicShareRepository shareRepository;
	private final AnalysisAccessService analysisAccessService;
	private final AnalysisJobRepository analysisJobRepository;
	private final AnalysisResultRepository analysisResultRepository;
	private final AnalysisResultReader analysisResultReader;
	private final TelegramRecipientRepository recipientRepository;
	private final EmailRecipientRepository emailRecipientRepository;
	private final AnalysisPublicShareProperties properties;

	public AnalysisPublicShareService(
			AnalysisPublicShareRepository shareRepository,
			AnalysisAccessService analysisAccessService,
			AnalysisJobRepository analysisJobRepository,
			AnalysisResultRepository analysisResultRepository,
			AnalysisResultReader analysisResultReader,
			TelegramRecipientRepository recipientRepository,
			EmailRecipientRepository emailRecipientRepository,
			AnalysisPublicShareProperties properties) {
		this.shareRepository = shareRepository;
		this.analysisAccessService = analysisAccessService;
		this.analysisJobRepository = analysisJobRepository;
		this.analysisResultRepository = analysisResultRepository;
		this.analysisResultReader = analysisResultReader;
		this.recipientRepository = recipientRepository;
		this.emailRecipientRepository = emailRecipientRepository;
		this.properties = properties;
	}

	@Transactional
	public IssuedAnalysisPublicShare issue(
			UUID analysisId, UUID recipientId, String ownerUsername) {
		AnalysisJob job = analysisAccessService.requireOwned(analysisId, ownerUsername);
		if (!analysisResultRepository.existsById(analysisId)) {
			throw new AnalysisResultNotReadyException(analysisId, job.getStatus());
		}
		recipientRepository.findByOwnerUsernameAndRecipientIdAndActiveTrue(
				ownerUsername, recipientId).orElseThrow(AnalysisPublicShareNotFoundException::new);

		Instant now = Instant.now();
		Instant expiresAt = now.plus(properties.ttl());
		String token = ShareTokens.issue(shareRepository::existsByTokenHash);
		AnalysisPublicShare share = shareRepository.save(AnalysisPublicShare.issue(
				analysisId, recipientId, ShareTokens.hash(token), now, expiresAt));
		return new IssuedAnalysisPublicShare(share.getShareId(), token, expiresAt);
	}

	@Transactional
	public IssuedAnalysisPublicShare issueForEmail(
			UUID analysisId, UUID emailRecipientId, String ownerUsername) {
		AnalysisJob job = analysisAccessService.requireOwned(analysisId, ownerUsername);
		if (!analysisResultRepository.existsById(analysisId)) {
			throw new AnalysisResultNotReadyException(analysisId, job.getStatus());
		}
		emailRecipientRepository.findByOwnerUsernameAndRecipientIdAndActiveTrue(
				ownerUsername, emailRecipientId)
				.orElseThrow(AnalysisPublicShareNotFoundException::new);

		Instant now = Instant.now();
		Instant expiresAt = now.plus(properties.ttl());
		String token = ShareTokens.issue(shareRepository::existsByTokenHash);
		AnalysisPublicShare share = shareRepository.save(AnalysisPublicShare.issueForEmail(
				analysisId, emailRecipientId, ShareTokens.hash(token), now, expiresAt));
		return new IssuedAnalysisPublicShare(share.getShareId(), token, expiresAt);
	}

	@Transactional(readOnly = true)
	public AnalysisPublicShareView resolve(String token) {
		if (!ShareTokens.valid(token)) {
			throw new AnalysisPublicShareNotFoundException();
		}
		AnalysisPublicShare share = shareRepository.findByTokenHash(ShareTokens.hash(token))
				.filter(candidate -> candidate.isAccessibleAt(Instant.now()))
				.orElseThrow(AnalysisPublicShareNotFoundException::new);
		String recipientOwner = recipientOwner(share);
		AnalysisJob job = analysisJobRepository.findById(share.getAnalysisId())
				.filter(candidate -> candidate.getOwnerUsername() != null)
				.filter(candidate -> candidate.getOwnerUsername().equals(recipientOwner))
				.orElseThrow(AnalysisPublicShareNotFoundException::new);
		AnalysisResultDetails result = analysisResultReader.getResult(
				share.getAnalysisId(), job.getOwnerUsername());
		return AnalysisPublicShareView.from(result, share.getExpiresAt());
	}

	@Transactional
	public void revoke(UUID shareId) {
		shareRepository.findById(shareId).ifPresent(share -> share.revoke(Instant.now()));
	}

	@Transactional
	public void revokeForRecipient(UUID recipientId) {
		Instant now = Instant.now();
		shareRepository.findAllByRecipientIdAndRevokedAtIsNull(recipientId)
				.forEach(share -> share.revoke(now));
	}

	@Transactional
	public void revokeForEmailRecipient(UUID emailRecipientId) {
		Instant now = Instant.now();
		shareRepository.findAllByEmailRecipientIdAndRevokedAtIsNull(emailRecipientId)
				.forEach(share -> share.revoke(now));
	}

	private String recipientOwner(AnalysisPublicShare share) {
		if (share.getRecipientId() != null && share.getEmailRecipientId() == null) {
			TelegramRecipient recipient = recipientRepository.findById(share.getRecipientId())
					.filter(TelegramRecipient::isActive)
					.orElseThrow(AnalysisPublicShareNotFoundException::new);
			return recipient.getOwnerUsername();
		}
		if (share.getRecipientId() == null && share.getEmailRecipientId() != null) {
			EmailRecipient recipient = emailRecipientRepository
					.findById(share.getEmailRecipientId())
					.filter(EmailRecipient::isActive)
					.orElseThrow(AnalysisPublicShareNotFoundException::new);
			return recipient.getOwnerUsername();
		}
		throw new AnalysisPublicShareNotFoundException();
	}
}
