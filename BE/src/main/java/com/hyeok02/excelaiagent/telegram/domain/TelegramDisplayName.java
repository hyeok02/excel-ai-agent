package com.hyeok02.excelaiagent.telegram.domain;

/**
 * 수신자 화면 이름을 정한다.
 *
 * 초대 링크에 붙인 이름을 가장 먼저 쓰고, 없으면 텔레그램이 준 이름과 아이디를
 * 차례로 본다. 셋 다 없을 수도 있어 마지막에 기본 이름을 둔다.
 */
final class TelegramDisplayName {
	private TelegramDisplayName() {
	}

	static String of(
			String invitationLabel, String username, String firstName, String lastName) {
		String label = normalize(invitationLabel);
		if (label != null) {
			return label;
		}
		String fullName = ((normalize(firstName) == null ? "" : firstName.trim()) + " "
				+ (normalize(lastName) == null ? "" : lastName.trim())).trim();
		if (!fullName.isBlank()) {
			return fullName;
		}
		String normalizedUsername = normalize(username);
		return normalizedUsername == null ? "Telegram 사용자" : "@" + normalizedUsername;
	}

	static String normalize(String value) {
		return value == null || value.isBlank() ? null : value.trim();
	}
}
