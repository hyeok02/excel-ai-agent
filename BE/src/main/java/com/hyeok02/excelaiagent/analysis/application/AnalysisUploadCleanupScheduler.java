package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;

import com.hyeok02.excelaiagent.analysis.storage.AnalysisFileStorage;
import com.hyeok02.excelaiagent.common.config.AppProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class AnalysisUploadCleanupScheduler {

	private static final Logger log = LoggerFactory.getLogger(AnalysisUploadCleanupScheduler.class);

	private final AnalysisFileStorage analysisFileStorage;
	private final AppProperties appProperties;

	public AnalysisUploadCleanupScheduler(
			AnalysisFileStorage analysisFileStorage,
			AppProperties appProperties) {
		this.analysisFileStorage = analysisFileStorage;
		this.appProperties = appProperties;
	}

	@Scheduled(
			fixedDelayString = "${app.storage.cleanup-interval:1h}",
			initialDelayString = "${app.storage.cleanup-initial-delay:1h}")
	public void deleteExpiredUploads() {
		Instant cutoff = Instant.now().minus(appProperties.storage().retention());
		try {
			int deletedCount = analysisFileStorage.deleteOlderThan(cutoff);
			if (deletedCount > 0) {
				log.info("보존 기간이 지난 분석 업로드 디렉터리 {}개를 정리했습니다.", deletedCount);
			}
		}
		catch (RuntimeException exception) {
			log.error("분석 업로드 파일 정리에 실패했습니다.", exception);
		}
	}
}
