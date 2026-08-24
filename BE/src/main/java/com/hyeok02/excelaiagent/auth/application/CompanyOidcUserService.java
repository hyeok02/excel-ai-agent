package com.hyeok02.excelaiagent.auth.application;

import java.util.Set;

import com.hyeok02.excelaiagent.auth.domain.AppUser;

import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserRequest;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserService;
import org.springframework.security.oauth2.client.userinfo.OAuth2UserService;
import org.springframework.security.oauth2.core.oidc.user.DefaultOidcUser;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.stereotype.Service;

@Service
public class CompanyOidcUserService implements OAuth2UserService<OidcUserRequest, OidcUser> {

	private final OidcUserService delegate = new OidcUserService();
	private final UserAccountService userAccountService;

	public CompanyOidcUserService(UserAccountService userAccountService) {
		this.userAccountService = userAccountService;
	}

	@Override
	public OidcUser loadUser(OidcUserRequest userRequest) {
		OidcUser oidcUser = delegate.loadUser(userRequest);
		String email = oidcUser.getEmail();
		String displayName = oidcUser.getFullName();
		AppUser appUser = userAccountService.findOrProvisionSsoUser(email, displayName);
		Set<GrantedAuthority> authorities = Set.of(
				new SimpleGrantedAuthority("ROLE_" + appUser.getRole().name()));

		if (oidcUser.getUserInfo() == null) {
			return new DefaultOidcUser(authorities, oidcUser.getIdToken(), "email");
		}
		return new DefaultOidcUser(
				authorities, oidcUser.getIdToken(), oidcUser.getUserInfo(), "email");
	}
}
