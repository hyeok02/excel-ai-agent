interface AuthInitialization<Config, User> {
  config: () => Promise<Config>
  csrf: () => Promise<unknown>
  user: () => Promise<User | null>
  isMounted: () => boolean
  isCurrent: () => boolean
  onConfig: (config: Config) => void
  onUser: (user: User | null) => void
  onSettled: () => void
}

/** Bootstrap must not supersede a login/logout that began while it was waiting. */
export const initializeAuthSession = async <Config, User>(
  options: AuthInitialization<Config, User>,
) => {
  try {
    const [config] = await Promise.all([options.config(), options.csrf()])
    if (!options.isMounted()) return
    options.onConfig(config)
    if (!options.isCurrent()) return
    const user = await options.user()
    if (options.isMounted() && options.isCurrent()) options.onUser(user)
  } catch {
    if (options.isMounted() && options.isCurrent()) options.onUser(null)
  } finally {
    if (options.isMounted()) options.onSettled()
  }
}
