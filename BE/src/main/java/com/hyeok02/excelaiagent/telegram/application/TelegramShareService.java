package com.hyeok02.excelaiagent.telegram.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.application.AnalysisResultDetails;
import com.hyeok02.excelaiagent.analysis.application.AnalysisResultReader;
import com.hyeok02.excelaiagent.telegram.integration.TelegramClient;
import org.springframework.stereotype.Service;

@Service
public class TelegramShareService {
	private final AnalysisResultReader resultReader;
	private final TelegramMessageFormatter messageFormatter;
	private final TelegramClient telegramClient;

	public TelegramShareService(
			AnalysisResultReader resultReader,
			TelegramMessageFormatter messageFormatter,
			TelegramClient telegramClient) {
		this.resultReader = resultReader;
		this.messageFormatter = messageFormatter;
		this.telegramClient = telegramClient;
	}

	public Instant share(UUID analysisId, String ownerUsername) {
		AnalysisResultDetails result = resultReader.getResult(analysisId, ownerUsername);
		telegramClient.sendMessage(messageFormatter.format(result));
		return Instant.now();
	}
}
