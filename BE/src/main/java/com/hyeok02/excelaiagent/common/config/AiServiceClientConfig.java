package com.hyeok02.excelaiagent.common.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
public class AiServiceClientConfig {

	@Bean
	public RestClient aiServiceRestClient(AppProperties appProperties) {
		AppProperties.AiService properties = appProperties.aiService();
		SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
		requestFactory.setConnectTimeout(properties.connectTimeout());
		requestFactory.setReadTimeout(properties.readTimeout());

		return RestClient.builder()
				.baseUrl(properties.baseUrl())
				.requestFactory(requestFactory)
				.build();
	}
}
