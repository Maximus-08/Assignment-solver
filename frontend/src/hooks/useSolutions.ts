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
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: (failureCount, error) => {
      if (error instanceof APIError && error.status === 404) {
        return false // Don't retry not found errors (solution might not exist yet)
      }
      if (error instanceof APIError && error.status >= 400 && error.status < 500) {
        return false // Don't retry client errors
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