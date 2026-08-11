package com.hyeok02.excelaiagent.common.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

	@Bean
	public OpenAPI excelAiAgentOpenApi() {
		return new OpenAPI()
				.info(new Info()
						.title("Excel AI Agent API")
						.description("Excel 분석 작업 접수 및 이력 조회를 위한 REST API")
						.version("v1"));
	}
}
