package com.hyeok02.excelaiagent.email.api;

import java.security.Principal;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.email.application.EmailRecipientManagementService;
import com.hyeok02.excelaiagent.email.application.EmailRecipientView;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/email/recipients")
public class EmailRecipientController {
	private final EmailRecipientManagementService recipientService;

	public EmailRecipientController(EmailRecipientManagementService recipientService) {
		this.recipientService = recipientService;
	}

	@GetMapping
	public List<EmailRecipientView> listRecipients(Principal principal) {
		return recipientService.listRecipients(actor(principal));
	}

	@PostMapping
	@ResponseStatus(HttpStatus.CREATED)
	public EmailRecipientView registerRecipient(
			@Valid @RequestBody RegisterEmailRecipientRequest request,
			Principal principal) {
		return recipientService.registerRecipient(
				actor(principal), request.email(), request.displayName());
	}

	@DeleteMapping("/{recipientId}")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	public void removeRecipient(@PathVariable UUID recipientId, Principal principal) {
		recipientService.deactivateRecipient(actor(principal), recipientId);
	}

	private String actor(Principal principal) {
		return principal == null ? "system" : principal.getName();
	}

	public record RegisterEmailRecipientRequest(
			@NotBlank(message = "이메일 주소를 입력해주세요.")
			@Email(message = "올바른 이메일 주소를 입력해주세요.")
			@Size(max = 255, message = "이메일 주소는 255자를 초과할 수 없습니다.")
			String email,
			@Size(max = 255, message = "수신자 이름은 255자를 초과할 수 없습니다.")
			String displayName) {
	}
}
