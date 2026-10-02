package com.hyeok02.excelaiagent.auth.api;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.UUID;

import com.hyeok02.excelaiagent.BackendApplication;
import com.hyeok02.excelaiagent.auth.domain.AppUserRepository;
import jakarta.servlet.http.HttpSession;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.test.web.servlet.MockMvc;

/** 인증·사용자 관리 테스트가 함께 쓰는 준비와 보조 메서드. */
@SpringBootTest(
		classes = BackendApplication.class,
		properties = {
				"app.auth.security-enabled=true",
				"app.auth.sso.enabled=false",
				"app.storage.upload-dir=build/test-auth-uploads"
		})
@AutoConfigureMockMvc
abstract class AuthControllerTestSupport {
	@Autowired
	protected MockMvc mockMvc;

	@Autowired
	protected AppUserRepository appUserRepository;

	protected MockHttpSession login(String username, String password) throws Exception {
		HttpSession session = mockMvc.perform(post("/api/v1/auth/login")
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("""
							{"username":"%s","password":"%s"}
							""".formatted(username, password)))
				.andExpect(status().isOk())
				.andReturn()
				.getRequest()
				.getSession(false);
		return (MockHttpSession) session;
	}

	protected String createUser(
			MockHttpSession adminSession, String username, String role) throws Exception {
		String response = mockMvc.perform(post("/api/v1/admin/users")
					.session(adminSession)
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("""
							{
							  "username":"%s",
							  "password":"employee1234",
							  "displayName":"상태 테스트 사용자",
							  "role":"%s"
							}
							""".formatted(username, role)))
				.andExpect(status().isCreated())
				.andReturn().getResponse().getContentAsString();
		return com.jayway.jsonpath.JsonPath.read(response, "$.id");
	}
}
