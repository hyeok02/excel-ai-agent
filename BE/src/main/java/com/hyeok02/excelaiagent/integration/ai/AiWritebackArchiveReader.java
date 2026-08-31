package com.hyeok02.excelaiagent.integration.ai;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import tools.jackson.databind.json.JsonMapper;

final class AiWritebackArchiveReader {
	private final JsonMapper jsonMapper;

	AiWritebackArchiveReader(JsonMapper jsonMapper) {
		this.jsonMapper = jsonMapper;
	}

	AiWritebackPackage read(byte[] content) {
		byte[] workbook = null;
		AiWritebackManifest manifest = null;
		try (ZipInputStream archive = new ZipInputStream(new ByteArrayInputStream(content))) {
			ZipEntry entry;
			while ((entry = archive.getNextEntry()) != null) {
				if (entry.isDirectory() || entry.getName().contains("..")) continue;
				byte[] value = copy(archive);
				if (entry.getName().startsWith("workbook.")) workbook = value;
				if ("manifest.json".equals(entry.getName())) {
					manifest = jsonMapper.readValue(value, AiWritebackManifest.class);
				}
			}
		}
		catch (IOException exception) {
			throw new AiServiceUnavailableException(exception);
		}
		if (workbook == null || manifest == null || !manifest.verified()) {
			throw new AiServiceUnavailableException();
		}
		return new AiWritebackPackage(workbook, manifest);
	}

	private byte[] copy(ZipInputStream input) throws IOException {
		ByteArrayOutputStream output = new ByteArrayOutputStream();
		input.transferTo(output);
		return output.toByteArray();
	}
}
