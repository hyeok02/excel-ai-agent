package com.hyeok02.excelaiagent.auth.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockHttpSession;

/** 로그인 전에 발급된 세션 ID로는 로그인 후 세션에 들어올 수 없어야 한다. */
class LoginSessionFixationTests extends AuthControllerTestSupport {

	@Test
	void changesTheSessionIdOnLogin() throws Exception {
		MockHttpSession preLogin = new MockHttpSession();
		String idBeforeLogin = preLogin.getId();

		mockMvc.perform(post("/api/v1/auth/login")
					.session(preLogin)
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("""
							{"username":"admin","password":"%s"}
							""".formatted(ADMIN_PASSWORD)))
				.andExpect(status().isOk());

		assertThat(preLogin.getId()).isNotEqualTo(idBeforeLogin);
	}

	@Test
	void leavesThePreLoginSessionIdUnauthenticated() throws Exception {
		MockHttpSession preLogin = new MockHttpSession();
		String stolenId = preLogin.getId();

		mockMvc.perform(post("/api/v1/auth/login")
					.session(preLogin)
					.with(csrf())
					.contentType(MediaType.APPLICATION_JSON)
					.content("""
							{"username":"admin","password":"%s"}
							""".formatted(ADMIN_PASSWORD)))
				.andExpect(status().isOk());

		MockHttpSession stolen = new MockHttpSession(null, stolenId);
		mockMvc.perform(get("/api/v1/auth/me").session(stolen))
				.andExpect(status().isNoContent());
	}
}
