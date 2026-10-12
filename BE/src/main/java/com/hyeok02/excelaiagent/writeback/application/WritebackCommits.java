package com.hyeok02.excelaiagent.writeback.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.writeback.domain.WorkbookWriteback;
import com.hyeok02.excelaiagent.writeback.domain.WorkbookWritebackRepository;
import com.hyeok02.excelaiagent.writeback.domain.WritebackStatus;
import com.hyeok02.excelaiagent.writeback.error.InvalidWritebackStateException;
import com.hyeok02.excelaiagent.writeback.error.WritebackNotFoundException;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * AI 호출이 끝난 뒤에만 열리는 짧은 쓰기 트랜잭션.
 *
 * 제안과 승인은 최대 150초가 걸리는 AI 호출을 기다린다. 그 전체를 한 트랜잭션으로
 * 감싸면 DB 커넥션을 그 시간 내내 쥐고 있어, 몇 건만 겹쳐도 풀이 말라 로그인까지
 * 막힌다. 그래서 읽기와 AI 호출은 트랜잭션 밖에서 하고 저장만 여기로 모은다.
 */
@Component
public class WritebackCommits {
	private final WorkbookWritebackRepository repository;

	public WritebackCommits(WorkbookWritebackRepository repository) {
		this.repository = repository;
	}

	@Transactional
	WorkbookWriteback save(WorkbookWriteback item) {
		return repository.save(item);
	}

	/**
	 * 승인을 확정한다. 제안 상태인지 여기서 다시 확인한다.
	 *
	 * AI가 응답하는 동안 같은 제안이 다른 요청으로 이미 승인·거절됐을 수 있다.
	 * 읽을 때 한 번 본 상태를 믿고 덮어쓰면 승인이 두 번 적용된다.
	 */
	@Transactional
	WorkbookWriteback applyVerified(
			UUID writebackId, String manifestJson, String actor, UUID baseWritebackId) {
		WorkbookWriteback item = repository.findById(writebackId)
				.orElseThrow(() -> new WritebackNotFoundException(writebackId));
		if (item.getStatus() != WritebackStatus.PROPOSED) {
			throw new InvalidWritebackStateException("승인 대기 중인 변경 제안만 처리할 수 있습니다.");
		}
		item.apply(manifestJson, actor, Instant.now(), baseWritebackId);
		return repository.save(item);
	}
}
