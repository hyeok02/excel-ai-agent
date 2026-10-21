interface AuthCallbackOptions {
  hasError: boolean
  refresh: () => Promise<unknown>
  onSuccess: () => void
  onErrorRedirect: () => void
  onFailure: () => void
  onRetry: () => void
  retryDelay?: number
}

/** Ignore superseded authentication results and cancel delayed redirects on exit. */
export const startAuthCallback = (options: AuthCallbackOptions) => {
  let active = true
  let retry: ReturnType<typeof setTimeout> | undefined
  const fail = () => {
    if (!active) return
    options.onFailure()
    retry = setTimeout(() => {
      if (active) options.onRetry()
    }, options.retryDelay ?? 1500)
  }
  if (options.hasError) options.onErrorRedirect()
  else
    void options.refresh().then((user) => {
      if (!active) return
      if (user) options.onSuccess()
      else fail()
    }, fail)
  return () => {
    active = false
    clearTimeout(retry)
  }
}
