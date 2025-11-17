// Assignment types
export interface Assignment {
  id: string
  title: string
  description: string
  subject?: string
  due_date?: string
  classroom_id?: string
  classroom_name?: string
  course_name?: string
  instructor?: string
  assignment_type?: string
  upload_date?: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  attachments?: Attachment[]
  solution?: Solution
  created_at: string
  updated_at: string
  source: 'classroom' | 'manual' | 'google_classroom' | 'manual_upload'
}

export interface Attachment {
  id: string
  filename: string
  url: string
  storage_url?: string
  mime_type: string
  file_type?: string
  size: number
  size_bytes?: number
  uploaded_at: string
  content_extracted?: boolean
}

export interface Solution {
  id: string
  assignment_id: string
  content: string
  steps?: string[]
  step_by_step?: Array<{
    step: string
    explanation: string
  }>
  explanation?: string
  reasoning?: string
  confidence_score?: number
  generated_at: string
  created_at?: string
  model_used?: string
  ai_model_used?: string
  processing_time?: number
  subject_area?: string
  quality_validated?: boolean
  feedback_rating?: number
  status: 'pending' | 'completed' | 'failed'
}

// API Response types
export interface APIResponse<T> {
  data: T
  message?: string
  timestamp: string
}

export interface ErrorResponse {
  error_code: string
  message: string
  details?: any
  timestamp: string
}

// Form data types
export interface ManualUploadData {
  title: string
  description: string
  subject?: string
  attachments?: File[]
}

// Pagination types
export interface PaginationParams {
  page?: number
  limit?: number
  search?: string
  subject?: string
  sort?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pages: number
  limit: number
}
