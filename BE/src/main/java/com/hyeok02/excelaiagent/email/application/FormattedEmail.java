package com.hyeok02.excelaiagent.email.application;

public record FormattedEmail(
		String subject,
		String plainTextBody,
		String htmlBody) {
}
