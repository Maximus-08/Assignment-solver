'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode, useState } from 'react'
import { APIError } from '@/lib/api'
import { isRetryableError, getRetryDelay } from '@/lib/errorHandling'

interface QueryProviderProps {
  children: ReactNode
}

export default function QueryProvider({ children }: QueryProviderProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            retry: (failureCount, error) => {
              // Don't retry if it's not a retryable error
              if (!isRetryableError(error)) {
                return false
              }
              
              // Don't retry more than 3 times
              if (failureCount >= 3) {
                return false
              }
              
              return true
            },
            retryDelay: (attemptIndex) => getRetryDelay(attemptIndex),
          },
          mutations: {
            retry: (failureCount, error) => {
              // Generally don't retry mutations unless it's a network error
              if (error instanceof APIError && error.status === 0) {
                return failureCount < 2
              }
              return false
            },
            retryDelay: (attemptIndex) => getRetryDelay(attemptIndex),
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}