package com.hyeok02.excelaiagent.sharing.domain;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

public interface AnalysisPublicShareRepository
		extends JpaRepository<AnalysisPublicShare, UUID> {

	Optional<AnalysisPublicShare> findByTokenHash(String tokenHash);

	boolean existsByTokenHash(String tokenHash);

	List<AnalysisPublicShare> findAllByRecipientIdAndRevokedAtIsNull(UUID recipientId);
}
