package com.hyeok02.excelaiagent.sharing.api;

import com.hyeok02.excelaiagent.sharing.application.AnalysisPublicShareService;
import com.hyeok02.excelaiagent.sharing.application.AnalysisPublicShareView;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/public/analysis-shares")
public class AnalysisPublicShareController {
	private final AnalysisPublicShareService service;

	public AnalysisPublicShareController(AnalysisPublicShareService service) {
		this.service = service;
	}

	@GetMapping("/{token}")
	public ResponseEntity<AnalysisPublicShareView> get(@PathVariable String token) {
		return ResponseEntity.ok()
				.cacheControl(CacheControl.noStore())
				.header("Referrer-Policy", "no-referrer")
				.header("X-Robots-Tag", "noindex, nofollow, noarchive")
				.body(service.resolve(token));
	}
}
