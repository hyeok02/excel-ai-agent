package com.hyeok02.excelaiagent.sharing.application;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;
import java.util.UUID;
import java.util.regex.Pattern;

import com.hyeok02.excelaiagent.analysis.application.AnalysisAccessService;
import com.hyeok02.excelaiagent.analysis.application.AnalysisResultDetails;
import com.hyeok02.excelaiagent.analysis.application.AnalysisResultReader;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResultRepository;
import com.hyeok02.excelaiagent.analysis.error.AnalysisResultNotReadyException;
import com.hyeok02.excelaiagent.common.config.AnalysisPublicShareProperties;
import com.hyeok02.excelaiagent.sharing.domain.AnalysisPublicShare;
import com.hyeok02.excelaiagent.sharing.domain.AnalysisPublicShareRepository;
import com.hyeok02.excelaiagent.sharing.error.AnalysisPublicShareNotFoundException;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipient;
import com.hyeok02.excelaiagent.telegram.domain.TelegramRecipientRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AnalysisPublicShareService {
	private static final int TOKEN_BYTES = 32;
	private static final int TOKEN_LENGTH = 43;
	private static final Pattern TOKEN_PATTERN = Pattern.compile("[A-Za-z0-9_-]{43}");

	private final AnalysisPublicShareRepository shareRepository;
	private final AnalysisAccessService analysisAccessService;
	private final AnalysisJobRepository analysisJobRepository;
	private final AnalysisResultRepository analysisResultRepository;
	private final AnalysisResultReader analysisResultReader;
	private final TelegramRecipientRepository recipientRepository;
	private final AnalysisPublicShareProperties properties;
	private final SecureRandom secureRandom = new SecureRandom();

	public AnalysisPublicShareService(
			AnalysisPublicShareRepository shareRepository,
			AnalysisAccessService analysisAccessService,
			AnalysisJobRepository analysisJobRepository,
			AnalysisResultRepository analysisResultRepository,
			AnalysisResultReader analysisResultReader,
			TelegramRecipientRepository recipientRepository,
			AnalysisPublicShareProperties properties) {
		this.shareRepository = shareRepository;
		this.analysisAccessService = analysisAccessService;
		this.analysisJobRepository = analysisJobRepository;
		this.analysisResultRepository = analysisResultRepository;
		this.analysisResultReader = analysisResultReader;
		this.recipientRepository = recipientRepository;
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
		String token = uniqueToken();
		AnalysisPublicShare share = shareRepository.save(AnalysisPublicShare.issue(
				analysisId, recipientId, hash(token), now, expiresAt));
		return new IssuedAnalysisPublicShare(share.getShareId(), token, expiresAt);
	}

	@Transactional(readOnly = true)
	public AnalysisPublicShareView resolve(String token) {
		if (!validToken(token)) {
			throw new AnalysisPublicShareNotFoundException();
		}
		AnalysisPublicShare share = shareRepository.findByTokenHash(hash(token))
				.filter(candidate -> candidate.isAccessibleAt(Instant.now()))
				.orElseThrow(AnalysisPublicShareNotFoundException::new);
		TelegramRecipient recipient = recipientRepository.findById(share.getRecipientId())
				.filter(TelegramRecipient::isActive)
				.orElseThrow(AnalysisPublicShareNotFoundException::new);
		AnalysisJob job = analysisJobRepository.findById(share.getAnalysisId())
				.filter(candidate -> candidate.getOwnerUsername() != null)
				.filter(candidate -> candidate.getOwnerUsername().equals(recipient.getOwnerUsername()))
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

	private String uniqueToken() {
		for (int attempt = 0; attempt < 3; attempt++) {
			byte[] bytes = new byte[TOKEN_BYTES];
			secureRandom.nextBytes(bytes);
			String token = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
			if (!shareRepository.existsByTokenHash(hash(token))) {
				return token;
			}
		}
		throw new IllegalStateException("고유한 분석 공유 토큰을 생성하지 못했습니다.");
	}

	private boolean validToken(String token) {
		return token != null && token.length() == TOKEN_LENGTH
				&& TOKEN_PATTERN.matcher(token).matches();
	}

	private String hash(String token) {
		try {
			MessageDigest digest = MessageDigest.getInstance("SHA-256");
			return HexFormat.of().formatHex(
					digest.digest(token.getBytes(StandardCharsets.UTF_8)));
		}
		catch (NoSuchAlgorithmException exception) {
			throw new IllegalStateException("SHA-256을 사용할 수 없습니다.", exception);
		}
	}
}
