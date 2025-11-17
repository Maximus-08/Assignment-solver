import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, APIError } from '@/lib/api'
import { Assignment, ManualUploadData } from '@/types'

// Query keys
export const assignmentKeys = {
  all: ['assignments'] as const,
  lists: () => [...assignmentKeys.all, 'list'] as const,
  list: (params: any) => [...assignmentKeys.lists(), params] as const,
  details: () => [...assignmentKeys.all, 'detail'] as const,
  detail: (id: string) => [...assignmentKeys.details(), id] as const,
  search: (query: string) => [...assignmentKeys.all, 'search', query] as const,
}

// Hooks for assignments
export function useAssignments(params?: {
  page?: number
  limit?: number
  search?: string
  subject?: string
  sort?: string
}) {
  return useQuery({
    queryKey: assignmentKeys.list(params),
    queryFn: () => apiClient.getAssignments(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: (failureCount, error) => {
      if (error instanceof APIError && error.status >= 400 && error.status < 500) {
        return false // Don't retry client errors
      }
      return failureCount < 3
    },
  })
}

export function useAssignment(id: string) {
  return useQuery({
    queryKey: assignmentKeys.detail(id),
    queryFn: () => apiClient.getAssignment(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000, // 2 minutes
    retry: (failureCount, error) => {
      if (error instanceof APIError && error.status === 404) {
        return false // Don't retry not found errors
      }
      if (error instanceof APIError && error.status >= 400 && error.status < 500) {
        return false // Don't retry client errors
      }
      return failureCount < 3
    },
  })
}

export function useSearchAssignments(query: string) {
  return useQuery({
    queryKey: assignmentKeys.search(query),
    queryFn: () => apiClient.searchAssignments(query),
    enabled: query.length > 0,
    staleTime: 1 * 60 * 1000, // 1 minute
  })
}

// Mutations
export function useCreateAssignment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ManualUploadData) => apiClient.createAssignment(data),
    onSuccess: (response) => {
      // Invalidate and refetch assignments list
      queryClient.invalidateQueries({ queryKey: assignmentKeys.lists() })
      
      // Add the new assignment to the cache
      queryClient.setQueryData(
        assignmentKeys.detail(response.data.id),
        response
      )
    },
    onError: (error) => {
      console.error('Failed to create assignment:', error)
    },
  })
}

export function useUpdateAssignment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Assignment> }) =>
      apiClient.updateAssignment(id, data),
    onSuccess: (response, variables) => {
      // Update the assignment in cache
      queryClient.setQueryData(
        assignmentKeys.detail(variables.id),
        response
      )
      
      // Invalidate lists to ensure consistency
      queryClient.invalidateQueries({ queryKey: assignmentKeys.lists() })
    },
    onError: (error) => {
      console.error('Failed to update assignment:', error)
    },
  })
}

export function useDeleteAssignment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => apiClient.deleteAssignment(id),
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: assignmentKeys.detail(id) })
      
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: assignmentKeys.lists() })
    },
    onError: (error) => {
      console.error('Failed to delete assignment:', error)
    },
  })
}