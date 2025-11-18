import { Assignment, Solution, APIResponse, ErrorResponse, ManualUploadData } from '@/types'
import { getSession } from 'next-auth/react'

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000'

class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: any
  ) {
    super(message)
    this.name = 'APIError'
  }
}

class APIClient {
  private baseURL: string
  private defaultHeaders: HeadersInit

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    
    // Get session token if available
    const session = await getSession()
    const headers: Record<string, string> = {
      ...this.defaultHeaders as Record<string, string>,
      ...(options.headers as Record<string, string> || {}),
    }
    
    // Add Authorization header if we have a backend token
    if (session?.backendToken) {
      headers['Authorization'] = `Bearer ${session.backendToken}`
    }
    
    const config: RequestInit = {
      ...options,
      headers,
      credentials: 'include',
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        let errorData: ErrorResponse
        try {
          errorData = await response.json()
        } catch {
          errorData = {
            error_code: 'UNKNOWN_ERROR',
            message: `HTTP ${response.status}: ${response.statusText}`,
            timestamp: new Date().toISOString(),
          }
        }
        
        throw new APIError(
          errorData.message,
          response.status,
          errorData.error_code,
          errorData.details
        )
      }

      // Handle empty responses
      if (response.status === 204) {
        return {} as T
      }

      const data = await response.json()
      return data
    } catch (error) {
      if (error instanceof APIError) {
        throw error
      }
      
      // Network or other errors
      throw new APIError(
        error instanceof Error ? error.message : 'Network error occurred',
        0,
        'NETWORK_ERROR'
      )
    }
  }

  // Assignment endpoints
  async getAssignments(params?: {
    page?: number
    limit?: number
    search?: string
    subject?: string
    sort?: string
  }): Promise<{ assignments: Assignment[]; total: number; page: number; per_page: number; has_next: boolean; has_prev: boolean }> {
    const searchParams = new URLSearchParams()
    
    if (params?.page) searchParams.append('page', params.page.toString())
    if (params?.limit) searchParams.append('limit', params.limit.toString())
    if (params?.search) searchParams.append('search', params.search)
    if (params?.subject) searchParams.append('subject', params.subject)
    if (params?.sort) searchParams.append('sort', params.sort)

    const query = searchParams.toString()
    const endpoint = `/api/v1/assignments${query ? `?${query}` : ''}`
    
    return this.request<{ assignments: Assignment[]; total: number; page: number; per_page: number; has_next: boolean; has_prev: boolean }>(endpoint)
  }

  async getAssignment(id: string): Promise<Assignment> {
    return this.request<Assignment>(`/api/v1/assignments/${id}`)
  }

  async getSolution(assignmentId: string): Promise<Solution> {
    return this.request<Solution>(`/api/v1/assignments/${assignmentId}/solution`)
  }

  async triggerSolution(assignmentId: string): Promise<{message: string; status: string; assignment_id: string}> {
    return this.request<{message: string; status: string; assignment_id: string}>(`/api/v1/assignments/${assignmentId}/solve`, {
      method: 'POST'
    })
  }

  async regenerateSolution(assignmentId: string): Promise<{message: string; status: string; assignment_id: string}> {
    return this.request<{message: string; status: string; assignment_id: string}>(`/api/v1/assignments/${assignmentId}/regenerate`, {
      method: 'POST'
    })
  }

  async resetAssignmentStatus(assignmentId: string): Promise<{message: string; assignment_id: string; status: string}> {
    return this.request<{message: string; assignment_id: string; status: string}>(`/api/v1/assignments/${assignmentId}/reset-status`, {
      method: 'POST'
    })
  }

  // Generic get/post methods for flexibility
  async get<T = any>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint)
  }

  async post<T = any>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined
    })
  }

  async createAssignment(data: ManualUploadData): Promise<APIResponse<Assignment>> {
    const formData = new FormData()
    formData.append('title', data.title)
    formData.append('description', data.description)
    if (data.subject) formData.append('subject', data.subject)
    
    // Add files
    if (data.attachments) {
      data.attachments.forEach((file, index) => {
        formData.append(`attachments`, file)
      })
    }

    return this.request<APIResponse<Assignment>>('/api/v1/assignments', {
      method: 'POST',
      headers: {
        // Don't set Content-Type for FormData, let browser set it with boundary
      },
      body: formData,
    })
  }

  async updateAssignment(id: string, data: Partial<Assignment>): Promise<APIResponse<Assignment>> {
    return this.request<APIResponse<Assignment>>(`/api/v1/assignments/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteAssignment(id: string): Promise<APIResponse<{}>> {
    return this.request<APIResponse<{}>>(`/api/v1/assignments/${id}`, {
      method: 'DELETE',
    })
  }

  async searchAssignments(query: string): Promise<APIResponse<Assignment[]>> {
    const searchParams = new URLSearchParams({ q: query })
    return this.request<APIResponse<Assignment[]>>(`/api/v1/assignments/search?${searchParams}`)
  }

  // Solution endpoints
  async getAssignmentSolution(assignmentId: string): Promise<APIResponse<Solution>> {
    return this.request<APIResponse<Solution>>(`/api/v1/assignments/${assignmentId}/solution`)
  }

  async createAssignmentSolution(assignmentId: string, solution: Partial<Solution>): Promise<APIResponse<Solution>> {
    return this.request<APIResponse<Solution>>(`/api/v1/assignments/${assignmentId}/solution`, {
      method: 'POST',
      body: JSON.stringify(solution),
    })
  }

  // File endpoints
  async uploadAttachment(assignmentId: string, file: File): Promise<APIResponse<{ url: string; filename: string }>> {
    const formData = new FormData()
    formData.append('file', file)

    return this.request<APIResponse<{ url: string; filename: string }>>(`/api/v1/assignments/${assignmentId}/attachments`, {
      method: 'POST',
      headers: {
        // Don't set Content-Type for FormData
      },
      body: formData,
    })
  }

  async downloadAttachment(assignmentId: string, fileId: string): Promise<Blob> {
    const response = await fetch(`${this.baseURL}/api/v1/assignments/${assignmentId}/attachments/${fileId}`)
    
    if (!response.ok) {
      throw new APIError(`Failed to download file`, response.status)
    }
    
    return response.blob()
  }

  // User endpoints
  async getUserProfile(): Promise<APIResponse<any>> {
    return this.request<APIResponse<any>>('/api/v1/users/profile')
  }

  // Google Classroom sync
  async syncGoogleClassroom(): Promise<APIResponse<{ synced: number; skipped: number; total_courses: number }>> {
    return this.request<APIResponse<{ synced: number; skipped: number; total_courses: number }>>('/api/v1/classroom/sync', {
      method: 'POST'
    })
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.request<{ status: string; timestamp: string }>('/health')
  }
}

// Create singleton instance
export const apiClient = new APIClient()

// Export types and utilities
export { APIError }
export type { APIResponse, ErrorResponse }