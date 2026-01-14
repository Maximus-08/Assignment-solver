import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, APIError } from '@/lib/api'
import { Solution } from '@/types'

// Query keys
export const solutionKeys = {
  all: ['solutions'] as const,
  byAssignment: (assignmentId: string) => [...solutionKeys.all, 'assignment', assignmentId] as const,
}

// Hooks for solutions
export function useAssignmentSolution(assignmentId: string) {
  return useQuery({
    queryKey: solutionKeys.byAssignment(assignmentId),
    queryFn: () => apiClient.getAssignmentSolution(assignmentId),
    enabled: !!assignmentId,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 15 * 60 * 1000, // Keep in cache for 15 minutes
    retry: (failureCount, error) => {
      // Check if error has status property (APIError-like) instead of instanceof
      if (error && typeof error === 'object' && 'status' in error) {
        const status = (error as any).status;
        if (status === 404 || (status >= 400 && status < 500)) {
          return false // Don't retry not found or client errors
        }
      }
      return failureCount < 3
    },
  })
}

// Mutations
export function useCreateAssignmentSolution() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ assignmentId, solution }: { assignmentId: string; solution: Partial<Solution> }) =>
      apiClient.createAssignmentSolution(assignmentId, solution),
    onSuccess: (response, variables) => {
      // Update the solution in cache
      queryClient.setQueryData(
        solutionKeys.byAssignment(variables.assignmentId),
        response
      )
    },
    onError: (error) => {
      console.error('Failed to create solution:', error)
    },
  })
}