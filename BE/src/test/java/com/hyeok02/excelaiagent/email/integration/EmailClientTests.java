package com.hyeok02.excelaiagent.email.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

import com.hyeok02.excelaiagent.common.config.EmailProperties;
import com.hyeok02.excelaiagent.email.error.EmailDeliveryException;
import com.hyeok02.excelaiagent.email.error.EmailNotConfiguredException;
import jakarta.mail.Message;
import jakarta.mail.Multipart;
import jakarta.mail.Part;
import jakarta.mail.Session;
import jakarta.mail.internet.MimeMessage;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.mail.MailSendException;
import org.springframework.mail.javamail.JavaMailSender;

class EmailClientTests {

	@Test
	void sendsUtf8MultipartAlternativeMessageWithSanitizedSubject() throws Exception {
		JavaMailSender mailSender = mock(JavaMailSender.class);
		MimeMessage mimeMessage = new MimeMessage(Session.getInstance(new Properties()));
		when(mailSender.createMimeMessage()).thenReturn(mimeMessage);
		EmailClient client = client(mailSender, true, "agent@example.com");

		client.send(
				"recipient@example.com",
				"분석\r\n결과",
				"상세 결과 평문 https://example.com/result",
				"<html lang=\"ko\"><body><strong>상세 결과 HTML</strong></body></html>");

		ArgumentCaptor<MimeMessage> message = ArgumentCaptor.forClass(MimeMessage.class);
		verify(mailSender).send(message.capture());
		MimeMessage parsed = roundTrip(message.getValue());
		assertThat(parsed.getFrom()[0].toString())
				.contains("Excel AI Agent", "agent@example.com");
		assertThat(parsed.getRecipients(Message.RecipientType.TO)[0].toString())
				.isEqualTo("recipient@example.com");
		assertThat(parsed.getSubject()).isEqualTo("분석 결과");

		List<MessagePart> parts = new ArrayList<>();
		collectMessageParts(parsed, parts);
		assertThat(parts).anySatisfy(part -> {
			assertThat(part.mimeType()).isEqualTo("text/plain");
			assertThat(part.contentType()).containsIgnoringCase("charset=UTF-8");
			assertThat(part.body()).contains("상세 결과 평문", "https://example.com/result");
		});
		assertThat(parts).anySatisfy(part -> {
			assertThat(part.mimeType()).isEqualTo("text/html");
			assertThat(part.contentType()).containsIgnoringCase("charset=UTF-8");
			assertThat(part.body()).contains("<strong>상세 결과 HTML</strong>");
		});
	}

	@Test
	void rejectsDeliveryWhenEmailIsDisabledOrMailSenderIsUnavailable() {
		JavaMailSender mailSender = mock(JavaMailSender.class);
		assertThatThrownBy(() -> client(mailSender, false, "agent@example.com")
				.send("recipient@example.com", "제목", "평문", "<p>본문</p>"))
				.isInstanceOf(EmailNotConfiguredException.class)
				.hasMessage("이메일 전송 설정이 필요합니다.");

		@SuppressWarnings("unchecked")
		ObjectProvider<JavaMailSender> emptyProvider = mock(ObjectProvider.class);
		when(emptyProvider.getIfAvailable()).thenReturn(null);
		EmailClient missingSender = new EmailClient(
				emptyProvider, new EmailProperties(true, "agent@example.com"));
		assertThatThrownBy(() -> missingSender.send(
				"recipient@example.com", "제목", "평문", "<p>본문</p>"))
				.isInstanceOf(EmailNotConfiguredException.class);
	}

	@Test
	void wrapsMailFailureWithoutExposingProviderDetails() {
		JavaMailSender mailSender = mock(JavaMailSender.class);
		when(mailSender.createMimeMessage())
				.thenReturn(new MimeMessage(Session.getInstance(new Properties())));
		org.mockito.Mockito.doThrow(new MailSendException("smtp secret detail"))
				.when(mailSender).send(any(MimeMessage.class));
		EmailClient client = client(mailSender, true, "agent@example.com");

		assertThatThrownBy(() -> client.send(
				"recipient@example.com", "제목", "평문", "<p>본문</p>"))
				.isInstanceOf(EmailDeliveryException.class)
				.hasMessage("이메일을 전송하지 못했습니다.")
				.hasMessageNotContaining("secret");
	}

	private MimeMessage roundTrip(MimeMessage message) throws Exception {
		message.saveChanges();
		ByteArrayOutputStream output = new ByteArrayOutputStream();
		message.writeTo(output);
		return new MimeMessage(
				Session.getInstance(new Properties()),
				new ByteArrayInputStream(output.toByteArray()));
	}

	private void collectMessageParts(Part part, List<MessagePart> parts) throws Exception {
		if (part.isMimeType("multipart/*")) {
			Multipart multipart = (Multipart) part.getContent();
			for (int index = 0; index < multipart.getCount(); index++) {
				collectMessageParts(multipart.getBodyPart(index), parts);
			}
			return;
		}
		if (part.isMimeType("text/plain")) {
			parts.add(new MessagePart("text/plain", part.getContentType(),
					String.valueOf(part.getContent())));
		}
		else if (part.isMimeType("text/html")) {
			parts.add(new MessagePart("text/html", part.getContentType(),
					String.valueOf(part.getContent())));
		}
	}

	private EmailClient client(
			JavaMailSender mailSender, boolean enabled, String fromAddress) {
		@SuppressWarnings("unchecked")
		ObjectProvider<JavaMailSender> provider = mock(ObjectProvider.class);
		when(provider.getIfAvailable()).thenReturn(mailSender);
		return new EmailClient(provider, new EmailProperties(enabled, fromAddress));
	}

	private record MessagePart(String mimeType, String contentType, String body) {
	}
}
