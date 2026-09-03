package com.hyeok02.excelaiagent.writeback.application;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.application.AnalysisAccessService;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;
import com.hyeok02.excelaiagent.analysis.error.AnalysisResultNotReadyException;
import com.hyeok02.excelaiagent.analysis.storage.AnalysisFileStorage;
import com.hyeok02.excelaiagent.integration.ai.AiWritebackClient;
import com.hyeok02.excelaiagent.integration.ai.AiWritebackPackage;
import com.hyeok02.excelaiagent.integration.ai.AiWritebackProposal;
import com.hyeok02.excelaiagent.integration.ai.NamedResource;
import com.hyeok02.excelaiagent.writeback.domain.WorkbookWriteback;
import com.hyeok02.excelaiagent.writeback.domain.WorkbookWritebackRepository;
import com.hyeok02.excelaiagent.writeback.domain.WritebackStatus;
import com.hyeok02.excelaiagent.writeback.error.InvalidWritebackStateException;
import com.hyeok02.excelaiagent.writeback.error.WritebackNotFoundException;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.ObjectMapper;

@Service
public class WorkbookWritebackService {
	private final AnalysisAccessService accessService;
	private final WorkbookWritebackRepository writebackRepository;
	private final AnalysisFileStorage fileStorage;
	private final AiWritebackClient aiClient;
	private final WritebackJson json;

	public WorkbookWritebackService(
			AnalysisAccessService accessService,
			WorkbookWritebackRepository writebackRepository,
			AnalysisFileStorage fileStorage, AiWritebackClient aiClient,
			ObjectMapper objectMapper) {
		this.accessService = accessService;
		this.writebackRepository = writebackRepository;
		this.fileStorage = fileStorage;
		this.aiClient = aiClient;
		this.json = new WritebackJson(objectMapper);
	}

	@Transactional
	public WritebackView propose(UUID analysisId, String instruction, String actor) {
		AnalysisJob job = completedJobWithSource(analysisId, actor);
		AiWritebackProposal proposal = aiClient.propose(original(job), instruction.trim());
		WorkbookWriteback item = WorkbookWriteback.proposed(
				analysisId, instruction.trim(), json.proposal(proposal),
				proposal.blocked(), actor, Instant.now());
		return WritebackView.from(writebackRepository.save(item), json);
	}

	@Transactional(readOnly = true)
	public List<WritebackView> list(UUID analysisId, String ownerUsername) {
		completedJob(analysisId, ownerUsername);
		return writebackRepository.findByAnalysisIdOrderByCreatedAtDesc(analysisId)
				.stream().map(item -> WritebackView.from(item, json)).toList();
	}

	@Transactional
	public WritebackView approve(UUID analysisId, UUID writebackId, boolean confirmed, String actor) {
		if (!confirmed) {
			throw new InvalidWritebackStateException("변경 전·후 값을 확인해야 승인할 수 있습니다.");
		}
		AnalysisJob job = completedJobWithSource(analysisId, actor);
		WorkbookWriteback item = find(analysisId, writebackId);
		requireProposed(item);
		AiWritebackProposal proposal = json.proposal(item.getProposalJson());
		AiWritebackPackage result = aiClient.apply(original(job), proposal.changes());
		fileStorage.storeWriteback(analysisId, writebackId, job.getFileExtension(), result.workbook());
		item.apply(json.manifest(result.manifest()), actor, Instant.now());
		return WritebackView.from(item, json);
	}

	@Transactional
	public WritebackView reject(UUID analysisId, UUID writebackId, String actor) {
		completedJob(analysisId, actor);
		WorkbookWriteback item = find(analysisId, writebackId);
		requireProposed(item);
		item.reject(actor, Instant.now());
		return WritebackView.from(item, json);
	}

	@Transactional(readOnly = true)
	public WritebackDownload download(
			UUID analysisId, UUID writebackId, String ownerUsername) {
		AnalysisJob job = completedJobWithSource(analysisId, ownerUsername);
		WorkbookWriteback item = find(analysisId, writebackId);
		if (item.getStatus() != WritebackStatus.APPLIED) {
			throw new InvalidWritebackStateException("검증이 완료된 수정본만 다운로드할 수 있습니다.");
		}
		Resource resource = fileStorage.loadWriteback(analysisId, writebackId, job.getFileExtension());
		return new WritebackDownload(resource, modifiedName(job.getOriginalFilename()));
	}

	private AnalysisJob completedJob(UUID analysisId, String ownerUsername) {
		AnalysisJob job = accessService.requireOwned(analysisId, ownerUsername);
		if (job.getStatus() != AnalysisStatus.COMPLETED) {
			throw new AnalysisResultNotReadyException(analysisId, job.getStatus());
		}
		return job;
	}

	private AnalysisJob completedJobWithSource(UUID analysisId, String ownerUsername) {
		return accessService.requireSourceAvailable(completedJob(analysisId, ownerUsername));
	}

	private WorkbookWriteback find(UUID analysisId, UUID id) {
		WorkbookWriteback item = writebackRepository.findById(id)
				.orElseThrow(() -> new WritebackNotFoundException(id));
		if (!item.getAnalysisId().equals(analysisId)) throw new WritebackNotFoundException(id);
		return item;
	}

	private Resource original(AnalysisJob job) {
		return new NamedResource(fileStorage.load(job.getAnalysisId(), job.getFileExtension()),
				job.getOriginalFilename());
	}

	private void requireProposed(WorkbookWriteback item) {
		if (item.getStatus() != WritebackStatus.PROPOSED) {
			throw new InvalidWritebackStateException("승인 대기 중인 변경 제안만 처리할 수 있습니다.");
		}
	}

	private String modifiedName(String original) {
		int dot = original.lastIndexOf('.');
		return dot < 0 ? original + "_modified" :
				original.substring(0, dot) + "_modified" + original.substring(dot);
	}
}
