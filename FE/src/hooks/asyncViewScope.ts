export interface ScopedResult<T> {
  value: T
  isActive: () => boolean
}

export const unwrapScopedResult = <T>(result: ScopedResult<T>): T => {
  if (!result.isActive()) throw new DOMException('View changed', 'AbortError')
  return result.value
}

export const applyScopedResult = <T, R>(
  result: ScopedResult<T>,
  effect: (value: T) => R,
): R | undefined => (result.isActive() ? effect(result.value) : undefined)

/** Each mount owns a distinct lease, including StrictMode effect replay. */
export const createAsyncViewScope = () => {
  let active: object | undefined
  return {
    mount: () => {
      const lease = {}
      active = lease
      return () => {
        if (active === lease) active = undefined
      }
    },
    run: async <T>(request: () => Promise<T>): Promise<ScopedResult<T>> => {
      const lease = active
      const isActive = () => lease !== undefined && active === lease
      if (!isActive()) throw new DOMException('View changed', 'AbortError')
      const result = { value: await request(), isActive }
      unwrapScopedResult(result)
      return result
    },
  }
}
