package com.hyeok02.excelaiagent.telegram.application;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HexFormat;

import com.hyeok02.excelaiagent.telegram.error.InvalidTelegramInvitationException;

/**
 * 텔레그램 초대 링크에 쓰는 토큰을 만들고 해시한다.
 *
 * 토큰 원문은 저장하지 않고 SHA-256 해시만 저장한다.
 */
final class TelegramInvitationTokens {
	private static final int TOKEN_BYTES = 32;
	private static final SecureRandom SECURE_RANDOM = new SecureRandom();

	private TelegramInvitationTokens() {
	}

	static String issue() {
		byte[] bytes = new byte[TOKEN_BYTES];
		SECURE_RANDOM.nextBytes(bytes);
		return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
	}

	static String hash(String rawToken) {
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
