package com.hyeok02.excelaiagent.integration.ai;

import org.springframework.core.io.Resource;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;

final class AiMultipartFile {
	private AiMultipartFile() {}

	static HttpEntity<Resource> named(Resource file) {
		String filename = file.getFilename() == null || file.getFilename().isBlank()
				? "workbook.xlsx" : file.getFilename();
		HttpHeaders headers = new HttpHeaders();
		headers.setContentDisposition(ContentDisposition.formData()
				.name("file").filename(filename).build());
		return new HttpEntity<>(file, headers);
	}
}
