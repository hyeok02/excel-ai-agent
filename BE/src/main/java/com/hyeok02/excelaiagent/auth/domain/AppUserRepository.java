package com.hyeok02.excelaiagent.auth.domain;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

public interface AppUserRepository extends JpaRepository<AppUser, UUID> {

	Optional<AppUser> findByUsernameIgnoreCase(String username);

	Optional<AppUser> findByEmailIgnoreCase(String email);

	boolean existsByUsernameIgnoreCase(String username);

	List<AppUser> findAllByOrderByCreatedAtDesc();
}
