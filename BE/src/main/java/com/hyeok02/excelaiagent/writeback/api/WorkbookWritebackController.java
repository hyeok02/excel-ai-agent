package com.hyeok02.excelaiagent.writeback.api;

import java.nio.charset.StandardCharsets;
import java.security.Principal;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.writeback.application.WorkbookWritebackService;
import com.hyeok02.excelaiagent.writeback.application.WritebackDownload;
import com.hyeok02.excelaiagent.writeback.application.WritebackView;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/analyses/{analysisId}/writebacks")
@Tag(name = "Excel Write-back", description = "승인 기반 Excel 수정 API")
public class WorkbookWritebackController {
	private final WorkbookWritebackService service;

	public WorkbookWritebackController(WorkbookWritebackService service) {
		this.service = service;
	}

	@PostMapping
	@Operation(summary = "Excel 변경 제안 생성")
	public WritebackView propose(
			@PathVariable UUID analysisId,
			@Valid @RequestBody WritebackProposalRequest request,
			Principal principal) {
		return service.propose(analysisId, request.instruction(), actor(principal));
	}

	@GetMapping
	@Operation(summary = "Excel 변경 감사 이력 조회")
	public List<WritebackView> list(@PathVariable UUID analysisId, Principal principal) {
		return service.list(analysisId, actor(principal));
	}

	@PostMapping("/{writebackId}/approve")
	@Operation(summary = "Excel 변경 제안 명시적 승인 및 복사본 생성")
	public WritebackView approve(
			@PathVariable UUID analysisId, @PathVariable UUID writebackId,
			@RequestBody WritebackApprovalRequest request, Principal principal) {
		return service.approve(
				analysisId, writebackId, request.confirmed(), actor(principal));
	}

	@PostMapping("/{writebackId}/reject")
	@Operation(summary = "Excel 변경 제안 거절")
	public WritebackView reject(
			@PathVariable UUID analysisId, @PathVariable UUID writebackId,
			Principal principal) {
		return service.reject(analysisId, writebackId, actor(principal));
	}

	@GetMapping("/{writebackId}/download")
	@Operation(summary = "검증된 Excel 수정본 다운로드")
	public ResponseEntity<?> download(
			@PathVariable UUID analysisId, @PathVariable UUID writebackId,
			Principal principal) {
		WritebackDownload download = service.download(
				analysisId, writebackId, actor(principal));
		ContentDisposition disposition = ContentDisposition.attachment()
				.filename(download.filename(), StandardCharsets.UTF_8).build();
		return ResponseEntity.ok()
				.header(HttpHeaders.CONTENT_DISPOSITION, disposition.toString())
				.body(download.resource());
	}

	private String actor(Principal principal) {
		return principal == null ? "system" : principal.getName();
	}
}
