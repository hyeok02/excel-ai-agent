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

class AuthControllerTests extends AuthControllerTestSupport {
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
}
