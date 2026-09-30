package com.hyeok02.excelaiagent.auth.domain;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import jakarta.persistence.LockModeType;

import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AppUserRepository extends JpaRepository<AppUser, UUID> {

	Optional<AppUser> findByUsernameIgnoreCase(String username);

	Optional<AppUser> findByEmailIgnoreCase(String email);

	boolean existsByUsernameIgnoreCase(String username);

	List<AppUser> findAllByOrderByCreatedAtDesc();

	@Query("select user.role from AppUser user where user.userId = :userId")
	Optional<UserRole> findRoleByUserId(@Param("userId") UUID userId);

	@Lock(LockModeType.PESSIMISTIC_WRITE)
	@Query("select user from AppUser user where user.userId = :userId")
	Optional<AppUser> findByUserIdForUpdate(@Param("userId") UUID userId);

	@Lock(LockModeType.PESSIMISTIC_WRITE)
	@Query("select user from AppUser user where user.role = :role order by user.username")
	List<AppUser> findAllByRoleForUpdate(@Param("role") UserRole role);
}
