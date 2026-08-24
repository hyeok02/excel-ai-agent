package com.hyeok02.excelaiagent.auth.api;

import java.time.Instant;
import java.util.List;

import com.hyeok02.excelaiagent.auth.application.UserAccountService;
import com.hyeok02.excelaiagent.auth.domain.AppUser;
import com.hyeok02.excelaiagent.auth.domain.UserRole;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/admin/users")
public class AdminUserController {

	private final UserAccountService userAccountService;

	public AdminUserController(UserAccountService userAccountService) {
		this.userAccountService = userAccountService;
	}

	@GetMapping
	public List<UserResponse> listUsers() {
		return userAccountService.listUsers().stream().map(UserResponse::from).toList();
	}

	@PostMapping
	@ResponseStatus(HttpStatus.CREATED)
	public UserResponse createUser(@Valid @RequestBody CreateUserRequest request) {
		return UserResponse.from(userAccountService.createLocalUser(
				request.username(), request.password(), request.displayName(), request.role()));
	}

	public record CreateUserRequest(
			@NotBlank(message = "아이디를 입력해주세요.")
			@Size(min = 3, max = 50, message = "아이디는 3~50자로 입력해주세요.")
			@Pattern(regexp = "^[A-Za-z0-9._-]+$", message = "아이디는 영문, 숫자, ., _, -만 사용할 수 있습니다.")
			String username,
			@NotBlank(message = "비밀번호를 입력해주세요.")
			@Size(min = 8, max = 72, message = "비밀번호는 8~72자로 입력해주세요.")
			String password,
			@NotBlank(message = "이름을 입력해주세요.")
			@Size(max = 100, message = "이름은 100자를 초과할 수 없습니다.")
			String displayName,
			@NotNull(message = "권한을 선택해주세요.") UserRole role) {
	}

	public record UserResponse(
			String id,
			String username,
			String displayName,
			String email,
			String role,
			String authProvider,
			boolean enabled,
			Instant createdAt) {

		private static UserResponse from(AppUser user) {
			return new UserResponse(
					user.getUserId().toString(), user.getUsername(), user.getDisplayName(),
					user.getEmail(), user.getRole().name(), user.getAuthProvider().name(),
					user.isEnabled(), user.getCreatedAt());
		}
	}
}
