package com.hyeok02.excelaiagent.sharing.application;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HexFormat;
import java.util.function.Predicate;
import java.util.regex.Pattern;

/**
 * 공개 공유 링크에 쓰는 토큰을 만들고 검사한다.
 *
 * 토큰 원문은 저장하지 않고 SHA-256 해시만 저장하므로, 링크를 아는 사람만
 * 열람할 수 있고 저장소가 노출돼도 링크가 복원되지 않는다.
 */
final class ShareTokens {
	private static final int TOKEN_BYTES = 32;
	private static final int TOKEN_LENGTH = 43;
	private static final Pattern TOKEN_PATTERN = Pattern.compile("[A-Za-z0-9_-]{43}");
	private static final SecureRandom SECURE_RANDOM = new SecureRandom();
	private static final int MAX_ATTEMPTS = 3;

	private ShareTokens() {
	}

	/** 이미 쓰고 있는 해시면 taken 이 true 를 돌려주고, 그때는 다시 뽑는다. */
	static String issue(Predicate<String> taken) {
		for (int attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
			byte[] bytes = new byte[TOKEN_BYTES];
			SECURE_RANDOM.nextBytes(bytes);
			String token = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
			if (!taken.test(hash(token))) {
				return token;
			}
		}
		throw new IllegalStateException("고유한 분석 공유 토큰을 생성하지 못했습니다.");
	}

	static boolean valid(String token) {
		return token != null && token.length() == TOKEN_LENGTH
				&& TOKEN_PATTERN.matcher(token).matches();
	}

	static String hash(String token) {
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
