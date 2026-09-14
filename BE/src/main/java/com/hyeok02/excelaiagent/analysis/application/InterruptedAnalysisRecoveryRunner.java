package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 분석 작업은 요청 스레드가 아닌 메모리 상의 실행기에서 처리되므로,
 * 서버가 내려가면 진행 중이던 작업을 이어받을 주체가 사라진다.
 * 남겨두면 QUEUED·PROCESSING 상태로 영원히 멈춰 있어 재분석도 조회도 되지 않기 때문에,
 * 기동 시점에 한 번 실패로 정리해 사용자가 상태를 확인할 수 있게 한다.
 */
@Component
public class InterruptedAnalysisRecoveryRunner implements ApplicationRunner {

	private static final String FAILURE_MESSAGE =
			"서버가 재시작되어 분석이 중단되었습니다. 파일을 다시 분석해주세요.";

	private static final Logger log =
			LoggerFactory.getLogger(InterruptedAnalysisRecoveryRunner.class);

	private final AnalysisJobRepository analysisJobRepository;

	public InterruptedAnalysisRecoveryRunner(AnalysisJobRepository analysisJobRepository) {
		this.analysisJobRepository = analysisJobRepository;
	}

	@Override
	@Transactional
	public void run(ApplicationArguments args) {
		int recoveredCount =
				analysisJobRepository.failInterruptedJobs(FAILURE_MESSAGE, Instant.now());
		if (recoveredCount > 0) {
			log.info("서버 재시작으로 중단된 분석 작업 {}개를 실패 처리했습니다.", recoveredCount);
		}
	}
}
