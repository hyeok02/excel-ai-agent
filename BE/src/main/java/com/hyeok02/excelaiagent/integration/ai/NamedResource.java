package com.hyeok02.excelaiagent.integration.ai;

import java.io.IOException;
import java.io.InputStream;

import org.springframework.core.io.AbstractResource;
import org.springframework.core.io.Resource;

public final class NamedResource extends AbstractResource {
	private final Resource delegate;
	private final String filename;

	public NamedResource(Resource delegate, String filename) {
		this.delegate = delegate;
		this.filename = filename;
	}

	@Override
	public String getDescription() {
		return delegate.getDescription();
	}

	@Override
	public String getFilename() {
		return filename;
	}

	@Override
	public InputStream getInputStream() throws IOException {
		return delegate.getInputStream();
	}

	@Override
	public long contentLength() throws IOException {
		return delegate.contentLength();
	}
}
