import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { assignmentKeys } from './useAssignments'

export function useUploadAttachment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ assignmentId, file }: { assignmentId: string; file: File }) =>
      apiClient.uploadAttachment(assignmentId, file),
    onSuccess: (response, variables) => {
      // Invalidate assignment details to refetch with new attachment
      queryClient.invalidateQueries({
        queryKey: assignmentKeys.detail(variables.assignmentId)
      })
    },
    onError: (error) => {
      console.error('Failed to upload attachment:', error)
    },
  })
}

export function useDownloadAttachment() {
  return useMutation({
    mutationFn: ({ assignmentId, fileId, filename }: { 
      assignmentId: string
      fileId: string
      filename: string
    }) => apiClient.downloadAttachment(assignmentId, fileId),
    onSuccess: (blob, variables) => {
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = variables.filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    },
    onError: (error) => {
      console.error('Failed to download attachment:', error)
    },
  })
}