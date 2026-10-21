import { QueryClientProvider } from '@tanstack/react-query'
import { type PropsWithChildren, useEffect, useState } from 'react'

import AuthProvider from '@/app/providers/AuthProvider'
import {
  createSessionQueryClient,
  disposeSessionQueryClient,
} from '@/app/providers/sessionQueryClient'

const SessionQueries = ({ children }: PropsWithChildren) => {
  const [queryClient] = useState(createSessionQueryClient)
  useEffect(() => () => disposeSessionQueryClient(queryClient), [queryClient])

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const AppProviders = ({ children }: PropsWithChildren) => (
  <AuthProvider>
    <SessionQueries>{children}</SessionQueries>
  </AuthProvider>
)

export default AppProviders
