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

@SpringBootTest(
		classes = BackendApplication.class,
		properties = {
				"app.auth.security-enabled=true",
				"app.auth.sso.enabled=false",
				"app.storage.upload-dir=build/test-auth-uploads"
		})
@AutoConfigureMockMvc
class AuthControllerTests {

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private AppUserRepository appUserRepository;

	@Test
	void protectsBusinessApisWithoutLogin() throws Exception {
		mockMvc.perform(get("/api/v1/analyses"))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("UNAUTHENTICATED"));
	}

	@Test
	void allowsOpaquePublicShareLookupWithoutLogin() throws Exception {
		mockMvc.perform(get("/api/v1/public/analysis-shares/{token}", "a".repeat(43)))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("ANALYSIS_SHARE_NOT_FOUND"))
				.andExpect(jsonPath("$.path")
						.value("/api/v1/public/analysis-shares/{token}"));
	}

	@Test
	void reportsEmptyCurrentUserWithoutLogin() throws Exception {
		mockMvc.perform(get("/api/v1/auth/me"))
				.andExpect(status().isNoContent());
	}

	@Test
	void permitsWebhookWithoutLoginOrCsrfButStillRequiresTelegramSecret() throws Exception {
		mockMvc.perform(post("/api/v1/telegram/webhook")
					.contentType(MediaType.APPLICATION_JSON)
					.content("{}"))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("INVALID_TELEGRAM_WEBHOOK_SECRET"));
	}

	@Test
	void logsInWithBootstrapAdminAccount() throws Exception {
		MockHttpSession session = login("admin", "admin1234");

		mockMvc.perform(get("/api/v1/auth/me").session(session))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.username").value("admin"))
				.andExpect(jsonPath("$.role").value("ADMIN"))
				.andExpect(jsonPath("$.authProvider").value("LOCAL"));
	}

	@Test
	void rejectsInvalidPassword() throws Exception {
		mockMvc.perform(post("/api/v1/auth/login")
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("""
							{"username":"admin","password":"wrong-password"}
							"""))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"));
	}

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

	private MockHttpSession login(String username, String password) throws Exception {
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

	private String createUser(
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
