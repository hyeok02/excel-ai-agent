package com.hyeok02.excelaiagent.telegram.api;

import java.security.Principal;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.telegram.application.CreatedTelegramInvitation;
import com.hyeok02.excelaiagent.telegram.application.TelegramInvitationView;
import com.hyeok02.excelaiagent.telegram.application.TelegramRecipientManagementService;
import com.hyeok02.excelaiagent.telegram.application.TelegramRecipientView;
import jakarta.validation.Valid;
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
@RequestMapping("/api/v1/telegram")
public class TelegramRecipientController {
	private final TelegramRecipientManagementService recipientService;

	public TelegramRecipientController(TelegramRecipientManagementService recipientService) {
		this.recipientService = recipientService;
	}

	@GetMapping("/recipients")
	public List<TelegramRecipientView> listRecipients(Principal principal) {
		return recipientService.listRecipients(actor(principal));
	}

	@DeleteMapping("/recipients/{recipientId}")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	public void removeRecipient(@PathVariable UUID recipientId, Principal principal) {
		recipientService.deactivateRecipient(actor(principal), recipientId);
	}

	@GetMapping("/invitations")
	public List<TelegramInvitationView> listInvitations(Principal principal) {
		return recipientService.listInvitations(actor(principal));
	}

	@PostMapping("/invitations")
	@ResponseStatus(HttpStatus.CREATED)
	public CreatedTelegramInvitation createInvitation(
			@Valid @RequestBody(required = false) CreateInvitationRequest request,
			Principal principal) {
		return recipientService.createInvitation(
				actor(principal), request == null ? null : request.label());
	}

	@DeleteMapping("/invitations/{invitationId}")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	public void revokeInvitation(@PathVariable UUID invitationId, Principal principal) {
		recipientService.revokeInvitation(actor(principal), invitationId);
	}

	private String actor(Principal principal) {
		return principal == null ? "system" : principal.getName();
	}

	public record CreateInvitationRequest(
			@Size(max = 255, message = "수신자 이름은 255자를 초과할 수 없습니다.")
			String label) {
	}
}
