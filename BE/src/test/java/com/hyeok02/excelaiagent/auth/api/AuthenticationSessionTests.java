package com.hyeok02.excelaiagent.auth.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import jakarta.servlet.http.Cookie;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.security.web.context.HttpSessionSecurityContextRepository;

class AuthenticationSessionTests extends AuthControllerTestSupport {

	@Test
	void rotatesExistingAnonymousSessionBeforeSavingAuthenticatedContext() throws Exception {
		MockHttpSession session = new MockHttpSession();
		session.setAttribute("saved-navigation", "/excel-analysis");
		String previousId = session.getId();
		var result = mockMvc.perform(post("/api/v1/auth/login")
					.session(session).with(csrf())
					.contentType(MediaType.APPLICATION_JSON).content(credentials("admin1234")))
				.andExpect(status().isOk()).andReturn();
		MockHttpSession authenticated = (MockHttpSession) result.getRequest().getSession(false);

		assertThat(authenticated).isNotNull();
		assertThat(authenticated.getId()).isNotEqualTo(previousId);
		assertThat(authenticated.getAttribute("saved-navigation")).isEqualTo("/excel-analysis");
		mockMvc.perform(get("/api/v1/auth/me").session(authenticated))
				.andExpect(status().isOk()).andExpect(jsonPath("$.username").value("admin"));
		mockMvc.perform(get("/api/v1/analyses").session(authenticated))
				.andExpect(status().isOk());
	}

	@Test
	void failedLoginDoesNotRotateOrAuthenticateAnonymousSession() throws Exception {
		MockHttpSession session = new MockHttpSession();
		String previousId = session.getId();
		mockMvc.perform(post("/api/v1/auth/login")
					.session(session).with(csrf())
					.contentType(MediaType.APPLICATION_JSON).content(credentials("incorrect")))
				.andExpect(status().isUnauthorized());

		assertThat(session.getId()).isEqualTo(previousId);
		assertThat(session.getAttribute(HttpSessionSecurityContextRepository.SPRING_SECURITY_CONTEXT_KEY))
				.isNull();
		mockMvc.perform(get("/api/v1/auth/me").session(session)).andExpect(status().isNoContent());
		mockMvc.perform(get("/api/v1/analyses").session(session)).andExpect(status().isUnauthorized());
	}

	@Test
	void logoutInvalidatesAuthenticatedSessionAndClearsAccess() throws Exception {
		MockHttpSession session = login("admin", "admin1234");
		String oldId = session.getId();
		mockMvc.perform(post("/api/v1/auth/logout").session(session).with(csrf()))
				.andExpect(status().isNoContent());

		assertThat(session.isInvalid()).isTrue();
		mockMvc.perform(get("/api/v1/auth/me").cookie(new Cookie("JSESSIONID", oldId)))
				.andExpect(status().isNoContent());
		mockMvc.perform(get("/api/v1/analyses").cookie(new Cookie("JSESSIONID", oldId)))
				.andExpect(status().isUnauthorized());
	}

	private String credentials(String password) {
		return "{\"username\":\"admin\",\"password\":\"%s\"}".formatted(password);
	}
}
