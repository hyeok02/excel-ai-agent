package com.hyeok02.excelaiagent.common.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {

	private final AppProperties appProperties;

	public WebConfig(AppProperties appProperties) {
		this.appProperties = appProperties;
	}

	@Override
	public void addCorsMappings(CorsRegistry registry) {
		registry.addMapping("/api/**")
				.allowedOrigins(appProperties.cors().allowedOrigins().toArray(String[]::new))
				.allowedMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
				.allowedHeaders("*")
				.allowCredentials(true)
				.maxAge(3600);
	}
}
