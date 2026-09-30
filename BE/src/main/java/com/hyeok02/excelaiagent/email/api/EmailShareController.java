package com.hyeok02.excelaiagent.email.api;

import java.security.Principal;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.email.application.EmailShareService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/analyses/{analysisId}/shares")
@Tag(name = "Analysis Sharing", description = "Excel 분석 결과 공유 API")
public class EmailShareController {
	private final EmailShareService emailShareService;

	public EmailShareController(EmailShareService emailShareService) {
		this.emailShareService = emailShareService;
	}

	@PostMapping("/email")
	@Operation(summary = "분석 결과를 이메일로 전송")
	public EmailShareResponse share(
			@PathVariable UUID analysisId,
			@RequestBody(required = false) EmailShareRequest request,
			Principal principal) {
		return emailShareService.share(
				analysisId, actor(principal), request == null || request.recipientIds() == null
						? List.of()
						: request.recipientIds());
	}

	private String actor(Principal principal) {
		return principal == null ? "system" : principal.getName();
	}

	public record EmailShareRequest(List<UUID> recipientIds) {
	}
}
