package com.hyeok02.excelaiagent.telegram.api;

import java.security.Principal;
import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.telegram.application.TelegramShareService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/analyses/{analysisId}/shares")
@Tag(name = "Analysis Sharing", description = "Excel 분석 결과 공유 API")
public class TelegramShareController {
	private final TelegramShareService telegramShareService;

	public TelegramShareController(TelegramShareService telegramShareService) {
		this.telegramShareService = telegramShareService;
	}

	@PostMapping("/telegram")
	@Operation(summary = "분석 결과를 텔레그램으로 전송")
	public TelegramShareResponse share(
			@PathVariable UUID analysisId, Principal principal) {
		Instant sentAt = telegramShareService.share(analysisId, actor(principal));
		return new TelegramShareResponse(sentAt);
	}

	private String actor(Principal principal) {
		return principal == null ? "system" : principal.getName();
	}
}
