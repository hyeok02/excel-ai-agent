import { QueryClient } from '@tanstack/react-query'

/** A cache belongs to one authenticated session, never to the browser lifetime. */
export const createSessionQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        refetchOnWindowFocus: false,
        staleTime: 30_000,
      },
      mutations: { retry: 0 },
    },
  })

export const disposeSessionQueryClient = (client: QueryClient) => {
  // Cancel before clearing so a late response cannot repopulate the old cache.
  void client.cancelQueries()
  client.clear()
}
