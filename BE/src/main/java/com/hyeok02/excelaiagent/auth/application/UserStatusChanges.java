package com.hyeok02.excelaiagent.auth.application;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.auth.domain.AppUser;
import com.hyeok02.excelaiagent.auth.domain.AppUserRepository;
import com.hyeok02.excelaiagent.auth.domain.UserRole;
import com.hyeok02.excelaiagent.auth.error.LastActiveAdminException;
import com.hyeok02.excelaiagent.auth.error.SelfDeactivationException;
import com.hyeok02.excelaiagent.auth.error.UserAccountNotFoundException;

/**
 * 계정을 켜고 끄는 규칙.
 *
 * 자기 자신은 끌 수 없고, 마지막으로 남은 활성 관리자도 끌 수 없다. 두 규칙 모두
 * 잠금을 건 상태에서 확인해야 동시에 들어온 요청이 함께 통과하지 않는다.
 */
final class UserStatusChanges {
	private final AppUserRepository appUserRepository;
	private final Clock clock;

	UserStatusChanges(AppUserRepository appUserRepository, Clock clock) {
		this.appUserRepository = appUserRepository;
		this.clock = clock;
	}

	AppUser apply(UUID userId, boolean enabled, UUID actorUserId) {
		if (!enabled && userId.equals(actorUserId)) {
			throw new SelfDeactivationException();
		}

		AppUser target;
		if (!enabled && appUserRepository.findRoleByUserId(userId)
				.orElseThrow(() -> new UserAccountNotFoundException(userId)) == UserRole.ADMIN) {
			List<AppUser> admins = appUserRepository.findAllByRoleForUpdate(UserRole.ADMIN);
			target = admins.stream()
					.filter(user -> user.getUserId().equals(userId))
					.findFirst()
					.orElseThrow(() -> new UserAccountNotFoundException(userId));
			if (target.isEnabled()
					&& admins.stream().filter(AppUser::isEnabled).count() <= 1) {
				throw new LastActiveAdminException();
			}
		}
		else {
			target = appUserRepository.findByUserIdForUpdate(userId)
					.orElseThrow(() -> new UserAccountNotFoundException(userId));
		}

		target.updateEnabled(enabled, Instant.now(clock));
		return target;
	}
}
