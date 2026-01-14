'use client'

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import FileUpload from './FileUpload'
import UploadProgress from './UploadProgress'
import { apiClient } from '@/lib/api'

interface FormData {
  title: string
  description: string
  subject: string
  dueDate: string
  files: File[]
}

interface ValidationErrors {
  title?: string
  description?: string
  subject?: string
  files?: string
}

export default function UploadForm() {
  const router = useRouter()
  const [formData, setFormData] = useState<FormData>({
    title: '',
    description: '',
    subject: '',  // Free-text, optional
    dueDate: '',
    files: [],
  })
  const [errors, setErrors] = useState<ValidationErrors>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'processing' | 'success' | 'error'>('idle')
  const [uploadedAssignmentId, setUploadedAssignmentId] = useState<string | null>(null)
  const [showSubjectSuggestions, setShowSubjectSuggestions] = useState(false)

  // Popular subject suggestions
  const suggestedSubjects = [
    'Mathematics',
    'Science',
    'Computer Science',
    'Physics',
    'Chemistry',
    'Biology',
    'English',
    'History',
    'Literature',
    'Art',
  ]
  
  // Filter suggestions based on input
  const filteredSuggestions = suggestedSubjects.filter(subject =>
    subject.toLowerCase().includes(formData.subject.toLowerCase())
  )

  const validateForm = (): boolean => {
    const newErrors: ValidationErrors = {}

    if (!formData.title.trim()) {
      newErrors.title = 'Assignment title is required'
    } else if (formData.title.length < 3) {
      newErrors.title = 'Title must be at least 3 characters long'
    } else if (formData.title.length > 200) {
      newErrors.title = 'Title must be less than 200 characters'
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Assignment description is required'
    } else if (formData.description.length < 10) {
      newErrors.description = 'Description must be at least 10 characters long'
    } else if (formData.description.length > 5000) {
      newErrors.description = 'Description must be less than 5000 characters'
    }

    // Subject is now optional - no validation needed

    if (formData.files.length > 10) {
      newErrors.files = 'Maximum 10 files allowed'
    }

    // Validate file sizes and types
    const maxFileSize = 10 * 1024 * 1024 // 10MB
    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
      'image/jpeg',
      'image/png',
      'image/gif',
      'image/webp',
    ]

    for (const file of formData.files) {
      if (file.size > maxFileSize) {
        newErrors.files = `File "${file.name}" is too large. Maximum size is 10MB.`
        break
      }
      if (!allowedTypes.includes(file.type)) {
        newErrors.files = `File "${file.name}" has an unsupported format. Please use PDF, Word, text, or image files.`
        break
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    // Clear error when user starts typing
    if (field in errors && errors[field as keyof ValidationErrors]) {
      setErrors(prev => ({ ...prev, [field as keyof ValidationErrors]: undefined }))
    }
  }

  const handleFilesChange = (files: File[]) => {
    setFormData(prev => ({ ...prev, files }))
    if (errors.files) {
      setErrors(prev => ({ ...prev, files: undefined }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)
    setUploadProgress(0)
    setUploadStatus('uploading')

    try {
      // Check if user is authenticated
      const { getSession } = await import('next-auth/react')
      const session = await getSession()
      
      if (!session) {
        alert('You must be logged in to upload assignments. Please sign in first.')
        setUploadStatus('error')
        setIsSubmitting(false)
        router.push('/auth/signin')
        return
      }

      // Step 1: Create the assignment (JSON only, no files)
      const response = await apiClient.createAssignment({
        title: formData.title,
        description: formData.description,
        subject: formData.subject || undefined,
      })

      console.log('Create assignment response:', response)
      const assignmentId = (response as any).id || response.data?.id
      
      if (!assignmentId) {
        throw new Error('No assignment ID returned from server')
      }
      
      setUploadProgress(30)
      
      // Step 2: Upload files if any
      if (formData.files.length > 0) {
        setUploadStatus('processing')
        for (let i = 0; i < formData.files.length; i++) {
          await apiClient.uploadAttachment(assignmentId, formData.files[i])
          setUploadProgress(30 + ((i + 1) / formData.files.length) * 70)
        }
      } else {
        setUploadProgress(100)
      }
      
      setUploadStatus('success')
      setUploadedAssignmentId(assignmentId)
      
      // Redirect to the assignment page after a short delay
      setTimeout(() => {
        router.push(`/assignments/${assignmentId}`)
      }, 2000)
    } catch (error: any) {
      console.error('Upload failed:', error)
      console.error('Error details:', {
        message: error?.message,
        status: error?.status,
        code: error?.code,
        details: error?.details
      })
      setUploadStatus('error')
      // Show more detailed error to user
      if (error?.message) {
        alert(`Upload failed: ${error.message}`)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReset = () => {
    setFormData({
      title: '',
      description: '',
      subject: '',
      dueDate: '',
      files: [],
    })
    setErrors({})
    setUploadProgress(0)
    setUploadStatus('idle')
    setUploadedAssignmentId(null)
  }

  if (uploadStatus === 'success') {
    return (
      <div className="bg-white rounded-lg shadow border border-gray-200 p-8 text-center">
        <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
          <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Upload Successful!</h2>
        <p className="text-gray-600 mb-6">
          Your assignment has been uploaded and is being processed by our AI. You&apos;ll be redirected to view the results shortly.
        </p>
        <div className="space-x-4">
          <button
            onClick={() => router.push(`/assignments/${uploadedAssignmentId}`)}
            className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2 rounded-md font-medium"
          >
            View Assignment
          </button>
          <button
            onClick={handleReset}
            className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-md font-medium"
          >
            Upload Another
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
      {(uploadStatus === 'uploading' || uploadStatus === 'processing') && (
        <UploadProgress 
          progress={uploadProgress} 
          status={uploadStatus}
          fileName={formData.files[0]?.name}
        />
      )}

      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        {/* Title Field */}
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
            Assignment Title *
          </label>
          <input
            type="text"
            id="title"
            value={formData.title}
            onChange={(e) => handleInputChange('title', e.target.value)}
            className={`block w-full px-3 py-2 border rounded-md shadow-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-1 ${
              errors.title
                ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500'
            }`}
            placeholder="Enter a descriptive title for your assignment"
            disabled={isSubmitting}
          />
          {errors.title && (
            <p className="mt-1 text-sm text-red-600">{errors.title}</p>
          )}
          <p className="mt-1 text-sm text-gray-500">
            {formData.title.length}/200 characters
          </p>
        </div>

        {/* Description Field */}
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
            Assignment Description *
          </label>
          <textarea
            id="description"
            rows={6}
            value={formData.description}
            onChange={(e) => handleInputChange('description', e.target.value)}
            className={`block w-full px-3 py-2 border rounded-md shadow-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-1 ${
              errors.description
                ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500'
            }`}
            placeholder="Provide detailed instructions, questions, or requirements for this assignment..."
            disabled={isSubmitting}
          />
          {errors.description && (
            <p className="mt-1 text-sm text-red-600">{errors.description}</p>
          )}
          <p className="mt-1 text-sm text-gray-500">
            {formData.description.length}/5000 characters
          </p>
        </div>

        {/* Subject and Due Date Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Subject Field - Free Text Input */}
          <div>
            <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-2">
              Subject (Optional)
            </label>
            <div className="relative">
              <input
                type="text"
                id="subject"
                value={formData.subject}
                onChange={(e) => {
                  handleInputChange('subject', e.target.value)
                  setShowSubjectSuggestions(true)
                }}
                onFocus={() => setShowSubjectSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSubjectSuggestions(false), 200)}
                className={`block w-full px-3 py-2 border rounded-md shadow-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-1 ${
                  errors.subject
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                    : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500'
                }`}
                placeholder="e.g., Mathematics, Biology, Computer Science..."
                disabled={isSubmitting}
              />
              
              {/* Suggestions Dropdown */}
              {showSubjectSuggestions && formData.subject && filteredSuggestions.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-48 overflow-y-auto">
                  {filteredSuggestions.map((subject) => (
                    <button
                      key={subject}
                      type="button"
                      onMouseDown={(e) => {
                        e.preventDefault()
                        handleInputChange('subject', subject)
                        setShowSubjectSuggestions(false)
                      }}
                      className="w-full text-left px-4 py-2 hover:bg-gray-50 text-gray-900 text-sm"
                    >
                      {subject}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {errors.subject && (
              <p className="mt-1 text-sm text-red-600">{errors.subject}</p>
            )}
            <p className="mt-1 text-sm text-gray-500">
              Leave blank to auto-detect from description
            </p>
          </div>

          {/* Due Date Field */}
          <div>
            <label htmlFor="dueDate" className="block text-sm font-medium text-gray-700 mb-2">
              Due Date (Optional)
            </label>
            <input
              type="datetime-local"
              id="dueDate"
              value={formData.dueDate}
              onChange={(e) => handleInputChange('dueDate', e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 focus:outline-none focus:ring-1 focus:border-primary-500 focus:ring-primary-500"
              disabled={isSubmitting}
            />
          </div>
        </div>

        {/* File Upload */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Attachments (Optional)
          </label>
          <FileUpload
            files={formData.files}
            onFilesChange={handleFilesChange}
            disabled={isSubmitting}
          />
          {errors.files && (
            <p className="mt-2 text-sm text-red-600">{errors.files}</p>
          )}
          <p className="mt-2 text-sm text-gray-500">
            Supported formats: PDF, Word documents, text files, and images (JPEG, PNG, GIF, WebP). Maximum 10MB per file, 10 files total.
          </p>
        </div>

        {/* Submit Buttons */}
        <div className="flex items-center justify-between pt-6 border-t border-gray-200">
          <button
            type="button"
            onClick={handleReset}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            disabled={isSubmitting}
          >
            Reset Form
          </button>
          
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-6 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <div className="flex items-center">
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Uploading...
              </div>
            ) : (
              'Upload Assignment'
            )}
          </button>
        </div>
      </form>

      {uploadStatus === 'error' && (
        <div className="bg-red-50 border-t border-red-200 px-6 py-4">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Upload Failed</h3>
              <p className="mt-1 text-sm text-red-700">
                There was an error uploading your assignment. Please try again.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}