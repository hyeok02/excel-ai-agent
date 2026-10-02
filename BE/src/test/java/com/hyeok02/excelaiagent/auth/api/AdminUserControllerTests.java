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

class AdminUserControllerTests extends AuthControllerTestSupport {
	@Test
	void adminCreatesLocalUser() throws Exception {
		MockHttpSession adminSession = login("admin", "admin1234");
		String username = "employee-" + UUID.randomUUID().toString().substring(0, 8);

		mockMvc.perform(post("/api/v1/admin/users")
					.session(adminSession)
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("""
							{
							  "username":"%s",
							  "password":"employee1234",
							  "displayName":"테스트 사용자",
							  "role":"USER"
							}
							""".formatted(username)))
				.andExpect(status().isCreated())
				.andExpect(jsonPath("$.username").value(username))
				.andExpect(jsonPath("$.role").value("USER"))
				.andExpect(jsonPath("$.authProvider").value("LOCAL"));

		MockHttpSession employeeSession = login(username, "employee1234");
		mockMvc.perform(get("/api/v1/admin/users").session(employeeSession))
				.andExpect(status().isForbidden());
	}

	@Test
	void validatesUserStatusRequests() throws Exception {
		MockHttpSession adminSession = login("admin", "admin1234");

		mockMvc.perform(patch("/api/v1/admin/users/not-a-uuid/status")
					.session(adminSession)
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"enabled\":false}"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_USER_ID"));

		mockMvc.perform(patch("/api/v1/admin/users/{userId}/status", UUID.randomUUID())
					.session(adminSession)
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("{}"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("VALIDATION_ERROR"))
				.andExpect(jsonPath("$.fieldErrors.enabled").value("활성 상태를 선택해주세요."));

		mockMvc.perform(patch("/api/v1/admin/users/{userId}/status", UUID.randomUUID())
					.session(adminSession)
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"enabled\":false}"))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("USER_NOT_FOUND"));
	}

	@Test
	void exposesSsoAvailabilityAndCsrfToken() throws Exception {
		mockMvc.perform(get("/api/v1/auth/config"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.ssoEnabled").value(false))
				.andExpect(jsonPath("$.ssoLoginPath").value("/oauth2/authorization/company"));

		mockMvc.perform(get("/api/v1/auth/csrf"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.token").isNotEmpty());
	}
}
