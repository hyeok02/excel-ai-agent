package com.hyeok02.excelaiagent.auth.api;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.UUID;

import com.hyeok02.excelaiagent.BackendApplication;
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

	@Test
	void protectsBusinessApisWithoutLogin() throws Exception {
		mockMvc.perform(get("/api/v1/analyses"))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("UNAUTHENTICATED"));
	}

	@Test
	void reportsEmptyCurrentUserWithoutLogin() throws Exception {
		mockMvc.perform(get("/api/v1/auth/me"))
				.andExpect(status().isNoContent());
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
}
