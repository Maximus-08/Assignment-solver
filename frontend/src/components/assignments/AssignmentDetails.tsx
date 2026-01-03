import { Assignment } from '@/types'

interface AssignmentDetailsProps {
  assignment: Assignment
}

export default function AssignmentDetails({ assignment }: AssignmentDetailsProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // Filter out meaningless or generic data
  const isValidField = (value: string | undefined): boolean => {
    if (!value) return false
    const trimmed = value.trim()
    // Filter out: empty strings, generic terms, numeric IDs, single words like "General" or "Test"
    if (trimmed.length === 0) return false
    if (/^\d+$/.test(trimmed) && trimmed.length > 10) return false // Numeric IDs (Google user IDs, etc.)
    if (['general', 'test', 'n/a', 'na', 'none', 'null', 'undefined'].includes(trimmed.toLowerCase())) return false
    return true
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'processing':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'pending':
        return 'bg-gray-100 text-gray-800 border-gray-200'
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getSourceIcon = (source: string) => {
    if (source === 'google_classroom') {
      return (
        <div className="flex items-center text-blue-600">
          <svg className="h-5 w-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
          <span>Google Classroom</span>
        </div>
      )
    }
    return (
      <div className="flex items-center text-gray-600">
        <svg className="h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <span>Manual Upload</span>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              {assignment.title}
            </h1>
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              {getSourceIcon(assignment.source)}
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(assignment.status)}`}>
                {assignment.status.charAt(0).toUpperCase() + assignment.status.slice(1)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-6">
        {/* Description */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Description</h2>
          <div className="prose prose-sm max-w-none text-gray-700">
            <p className="whitespace-pre-wrap">{assignment.description}</p>
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Course Information</h3>
              <div className="mt-2 space-y-2">
                {isValidField(assignment.subject) && (
                  <div className="flex items-center">
                    <svg className="h-4 w-4 text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                    </svg>
                    <div>
                      <span className="text-xs text-gray-500">Subject:</span>
                      <span className="text-sm text-gray-900 ml-1">{assignment.subject}</span>
                    </div>
                  </div>
                )}
                {isValidField(assignment.course_name) && (
                  <div className="flex items-center">
                    <svg className="h-4 w-4 text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                    <div>
                      <span className="text-xs text-gray-500">Course:</span>
                      <span className="text-sm text-gray-900 ml-1">{assignment.course_name}</span>
                    </div>
                  </div>
                )}
                {isValidField(assignment.classroom_name) && (
                  <div className="flex items-center">
                    <svg className="h-4 w-4 text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                    </svg>
                    <div>
                      <span className="text-xs text-gray-500">Classroom:</span>
                      <span className="text-sm text-gray-900 ml-1">{assignment.classroom_name}</span>
                    </div>
                  </div>
                )}
                {isValidField(assignment.instructor) && (
                  <div className="flex items-center">
                    <svg className="h-4 w-4 text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    <div>
                      <span className="text-xs text-gray-500">Instructor:</span>
                      <span className="text-sm text-gray-900 ml-1">{assignment.instructor}</span>
                    </div>
                  </div>
                )}
                {isValidField(assignment.assignment_type) && (
                  <div className="flex items-center">
                    <svg className="h-4 w-4 text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                    <div>
                      <span className="text-xs text-gray-500">Type:</span>
                      <span className="text-sm text-gray-900 ml-1 capitalize">{assignment.assignment_type.replace('_', ' ')}</span>
                    </div>
                  </div>
                )}
                {!isValidField(assignment.subject) && !isValidField(assignment.course_name) && 
                 !isValidField(assignment.instructor) && !isValidField(assignment.assignment_type) && (
                  <p className="text-sm text-gray-500 italic">No course information available</p>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Timeline</h3>
              <div className="mt-2 space-y-2">
                <div className="flex items-center">
                  <svg className="h-4 w-4 text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <div>
                    <span className="text-sm text-gray-500">Uploaded:</span>
                    <span className="text-sm text-gray-900 ml-1">{formatDate(assignment.upload_date || assignment.created_at)}</span>
                  </div>
                </div>
                {assignment.due_date && (
                  <div className="flex items-center">
                    <svg className="h-4 w-4 text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div>
                      <span className="text-sm text-gray-500">Due:</span>
                      <span className="text-sm text-gray-900 ml-1">{formatDate(assignment.due_date)}</span>
                    </div>
                  </div>
                )}
                <div className="flex items-center">
                  <svg className="h-4 w-4 text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <div>
                    <span className="text-sm text-gray-500">Last updated:</span>
                    <span className="text-sm text-gray-900 ml-1">{formatDate(assignment.updated_at)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}