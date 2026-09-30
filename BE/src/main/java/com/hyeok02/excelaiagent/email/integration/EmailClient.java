package com.hyeok02.excelaiagent.email.integration;

import java.io.UnsupportedEncodingException;
import java.nio.charset.StandardCharsets;

import com.hyeok02.excelaiagent.common.config.EmailProperties;
import com.hyeok02.excelaiagent.email.error.EmailDeliveryException;
import com.hyeok02.excelaiagent.email.error.EmailNotConfiguredException;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.mail.MailException;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Component;

@Component
public class EmailClient {
	private final ObjectProvider<JavaMailSender> mailSenderProvider;
	private final EmailProperties properties;

	public EmailClient(
			ObjectProvider<JavaMailSender> mailSenderProvider,
			EmailProperties properties) {
		this.mailSenderProvider = mailSenderProvider;
		this.properties = properties;
	}

	public void send(
			String recipientAddress,
			String subject,
			String plainTextBody,
			String htmlBody) {
		JavaMailSender mailSender = mailSenderProvider.getIfAvailable();
		if (!properties.configured() || mailSender == null) {
			throw new EmailNotConfiguredException();
		}
		if (recipientAddress == null || recipientAddress.isBlank()) {
			throw new EmailDeliveryException();
		}
		try {
			MimeMessage message = mailSender.createMimeMessage();
			MimeMessageHelper helper = new MimeMessageHelper(
					message,
					MimeMessageHelper.MULTIPART_MODE_MIXED_RELATED,
					StandardCharsets.UTF_8.name());
			helper.setFrom(properties.fromAddress(), "Excel AI Agent");
			helper.setTo(recipientAddress);
			helper.setSubject(sanitizeHeader(subject));
			helper.setText(
					plainTextBody == null ? "" : plainTextBody,
					htmlBody == null ? "" : htmlBody);
			mailSender.send(message);
		}
		catch (MailException | MessagingException | UnsupportedEncodingException
				| IllegalArgumentException exception) {
			throw new EmailDeliveryException(exception);
		}
	}

	private String sanitizeHeader(String value) {
		if (value == null || value.isBlank()) {
			return "Excel 분석 결과";
		}
		return value.replaceAll("[\\r\\n]+", " ").trim();
	}
}
