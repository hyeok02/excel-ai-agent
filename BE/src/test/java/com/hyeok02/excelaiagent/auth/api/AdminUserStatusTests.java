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

class AdminUserStatusTests extends AuthControllerTestSupport {
	@Test
	void adminDeactivatesAndReactivatesUserAndExistingSessionIsRevoked() throws Exception {
		MockHttpSession adminSession = login("admin", "admin1234");
		String username = "status-" + UUID.randomUUID().toString().substring(0, 8);
		String userId = createUser(adminSession, username, "USER");
		MockHttpSession employeeSession = login(username, "employee1234");
		MockHttpSession accountSwitchSession = login(username, "employee1234");
		MockHttpSession currentUserSession = login(username, "employee1234");

		mockMvc.perform(patch("/api/v1/admin/users/{userId}/status", userId)
					.session(adminSession)
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"enabled\":false}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.id").value(userId))
				.andExpect(jsonPath("$.enabled").value(false));

		mockMvc.perform(get("/api/v1/auth/config").session(employeeSession))
				.andExpect(status().isOk());
		mockMvc.perform(get("/api/v1/auth/csrf").session(employeeSession))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.token").isNotEmpty());

		mockMvc.perform(post("/api/v1/auth/login")
					.session(accountSwitchSession)
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"username\":\"admin\",\"password\":\"admin1234\"}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.username").value("admin"));

		mockMvc.perform(get("/api/v1/auth/me").session(currentUserSession))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("ACCOUNT_DISABLED"));

		mockMvc.perform(get("/api/v1/analyses").session(employeeSession))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("ACCOUNT_DISABLED"));

		mockMvc.perform(post("/api/v1/auth/login")
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"username\":\"%s\",\"password\":\"employee1234\"}"
							.formatted(username)))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"));

		mockMvc.perform(patch("/api/v1/admin/users/{userId}/status", userId)
					.session(adminSession)
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"enabled\":true}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.enabled").value(true));

		login(username, "employee1234");
	}

	@Test
	void adminCannotDeactivateOwnAccount() throws Exception {
		MockHttpSession adminSession = login("admin", "admin1234");
		String adminId = appUserRepository.findByUsernameIgnoreCase("admin").orElseThrow()
				.getUserId().toString();

		mockMvc.perform(patch("/api/v1/admin/users/{userId}/status", adminId)
					.session(adminSession)
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"enabled\":false}"))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("SELF_DEACTIVATION_NOT_ALLOWED"));
	}
}
