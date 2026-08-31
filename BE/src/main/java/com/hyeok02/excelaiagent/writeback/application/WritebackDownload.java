package com.hyeok02.excelaiagent.writeback.application;

import org.springframework.core.io.Resource;

public record WritebackDownload(Resource resource, String filename) {}
