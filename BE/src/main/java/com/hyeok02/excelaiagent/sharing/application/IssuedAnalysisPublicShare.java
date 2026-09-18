package com.hyeok02.excelaiagent.sharing.application;

import java.time.Instant;
import java.util.UUID;

public record IssuedAnalysisPublicShare(
		UUID shareId,
		String token,
		Instant expiresAt) {
}
