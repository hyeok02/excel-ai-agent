package com.hyeok02.excelaiagent.analysis.api;

import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.application.AnalysisHistoryPage;
import com.hyeok02.excelaiagent.analysis.application.AnalysisDetails;
import com.hyeok02.excelaiagent.analysis.application.AnalysisSubmission;
import com.hyeok02.excelaiagent.analysis.application.AnalysisSubmissionService;
import com.hyeok02.excelaiagent.analysis.application.AnalysisResultDetails;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/analyses")
@Validated
@Tag(name = "Excel Analysis", description = "Excel 분석 작업 API")
public class AnalysisController {

	private final AnalysisSubmissionService analysisSubmissionService;

	public AnalysisController(AnalysisSubmissionService analysisSubmissionService) {
		this.analysisSubmissionService = analysisSubmissionService;
	}

	@PostMapping
	@Operation(summary = "Excel 분석 작업 접수")
	public ResponseEntity<AnalysisSubmission> submit(
			@RequestPart("file") MultipartFile file,
			@RequestParam("mode") AnalysisMode mode) {
		AnalysisSubmission response = analysisSubmissionService.submit(file, mode);
		return ResponseEntity.accepted().body(response);
	}

	@GetMapping
	@Operation(summary = "분석 이력 검색 및 목록 조회")
	public AnalysisHistoryPage getHistory(
			@Parameter(description = "분석 모드 필터")
			@RequestParam(required = false) AnalysisMode mode,
			@Parameter(description = "원본 파일명 검색어")
			@RequestParam(required = false) String filename,
			@RequestParam(defaultValue = "0") @Min(0) int page,
			@RequestParam(defaultValue = "20") @Min(1) @Max(100) int size) {
		return analysisSubmissionService.getHistory(mode, filename, page, size);
	}

	@GetMapping("/{analysisId}")
	@Operation(summary = "분석 작업 상세 조회")
	public AnalysisDetails getDetails(@PathVariable UUID analysisId) {
		return analysisSubmissionService.getDetails(analysisId);
	}

	@GetMapping("/{analysisId}/result")
	@Operation(summary = "분석 작업 결과 조회")
	public AnalysisResultDetails getResult(@PathVariable UUID analysisId) {
		return analysisSubmissionService.getResult(analysisId);
	}

	@DeleteMapping("/{analysisId}")
	@Operation(summary = "분석 작업 삭제")
	public ResponseEntity<Void> delete(@PathVariable UUID analysisId) {
		analysisSubmissionService.delete(analysisId);
		return ResponseEntity.noContent().build();
	}
}
