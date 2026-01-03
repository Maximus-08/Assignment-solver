'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Assignment, Solution } from '@/types'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import AssignmentDetails from '@/components/assignments/AssignmentDetails'
import SolutionView from '@/components/assignments/SolutionView'
import AttachmentsList from '@/components/assignments/AttachmentsList'

export default function AssignmentPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const params = useParams()
  const assignmentId = params.id as string

  const [assignment, setAssignment] = useState<Assignment | null>(null)
  const [solution, setSolution] = useState<Solution | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [solving, setSolving] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [solveMessage, setSolveMessage] = useState<string>('')

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin')
    }
  }, [status, router])

  useEffect(() => {
    const fetchAssignmentAndSolution = async () => {
      if (!assignmentId) return

      setLoading(true)
      setError(null)

      try {
        const { apiClient } = await import('@/lib/api')
        
        // Fetch assignment details
        const assignmentResponse = await apiClient.getAssignment(assignmentId)
        console.log('Assignment details:', assignmentResponse)
        setAssignment(assignmentResponse)

        // Try to fetch solution if available
        try {
          const solutionResponse = await apiClient.getSolution(assignmentId)
          console.log('Solution:', solutionResponse)
          setSolution(solutionResponse)
        } catch (solutionError: any) {
          // Solution not found is expected for pending assignments
          if (solutionError?.status !== 404) {
            console.error('Error fetching solution:', solutionError)
          }
        }
      } catch (err: any) {
        setError(err?.message || 'Failed to load assignment details. Please try again.')
        console.error('Error fetching assignment:', err)
      } finally {
        setLoading(false)
      }
    }

    if (session) {
      fetchAssignmentAndSolution()
    }
  }, [assignmentId, session])

  const handleSolveAssignment = async () => {
    if (!assignment) return
    
    setSolving(true)
    setSolveMessage('')
    
    try {
      const { apiClient } = await import('@/lib/api')
      const result = await apiClient.triggerSolution(assignmentId)
      
      setSolveMessage(result.message)
      
      // Update assignment status locally
      setAssignment({
        ...assignment,
        status: 'processing'
      })
      
      // Poll for solution every 5 seconds
      const pollInterval = setInterval(async () => {
        try {
          const updatedAssignment = await apiClient.getAssignment(assignmentId)
          setAssignment(updatedAssignment)
          
          if (updatedAssignment.status === 'completed') {
            // Fetch the solution
            try {
              const newSolution = await apiClient.getSolution(assignmentId)
              setSolution(newSolution)
              setSolveMessage('✓ Solution generated successfully!')
              clearInterval(pollInterval)
            } catch (err) {
              console.error('Error fetching solution:', err)
            }
          } else if (updatedAssignment.status === 'failed') {
            setSolveMessage('✗ Solution generation failed')
            clearInterval(pollInterval)
          }
        } catch (err) {
          console.error('Error polling assignment:', err)
          clearInterval(pollInterval)
        }
      }, 5000)
      
      // Stop polling after 5 minutes
      setTimeout(() => clearInterval(pollInterval), 300000)
      
    } catch (error: any) {
      console.error('Solve error:', error)
      setSolveMessage(`✗ ${error?.message || 'Failed to start solving'}`)
    } finally {
      setSolving(false)
    }
  }

  const handleRegenerateSolution = async () => {
    if (!assignment) return
    
    if (!confirm('Are you sure you want to regenerate the solution? The current solution will be deleted.')) {
      return
    }
    
    setRegenerating(true)
    setSolution(null) // Clear current solution
    setSolveMessage('')
    
    try {
      const { apiClient } = await import('@/lib/api')
      const result = await apiClient.regenerateSolution(assignmentId)
      
      setSolveMessage(result.message)
      
      // Update assignment status locally
      setAssignment({
        ...assignment,
        status: 'processing'
      })
      
      // Poll for solution every 5 seconds
      const pollInterval = setInterval(async () => {
        try {
          const updatedAssignment = await apiClient.getAssignment(assignmentId)
          setAssignment(updatedAssignment)
          
          if (updatedAssignment.status === 'completed') {
            // Fetch the new solution
            try {
              const newSolution = await apiClient.getSolution(assignmentId)
              setSolution(newSolution)
              setSolveMessage('✓ Solution regenerated successfully!')
              clearInterval(pollInterval)
            } catch (err) {
              console.error('Error fetching solution:', err)
            }
          } else if (updatedAssignment.status === 'failed') {
            setSolveMessage('✗ Solution regeneration failed')
            clearInterval(pollInterval)
          }
        } catch (err) {
          console.error('Error polling assignment:', err)
          clearInterval(pollInterval)
        }
      }, 5000)
      
      // Stop polling after 5 minutes
      setTimeout(() => clearInterval(pollInterval), 300000)
      
    } catch (error: any) {
      console.error('Regenerate error:', error)
      setSolveMessage(`✗ ${error?.message || 'Failed to regenerate solution'}`)
    } finally {
      setRegenerating(false)
    }
  }

  if (status === 'loading' || loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!session) {
    return null
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <div className="text-red-600 mb-2">
            <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-red-800 mb-2">Error Loading Assignment</h3>
          <p className="text-red-600 mb-4">{error}</p>
          <div className="space-x-4">
            <button
              onClick={() => window.location.reload()}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium"
            >
              Try Again
            </button>
            <Link
              href="/assignments"
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md text-sm font-medium"
            >
              Back to Assignments
            </Link>
          </div>
        </div>
      </div>
    )
  }

  if (!assignment) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <div className="text-gray-400 mb-4">
            <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Assignment not found</h3>
          <p className="text-gray-600 mb-4">The assignment you&apos;re looking for doesn&apos;t exist or has been removed.</p>
          <Link
            href="/assignments"
            className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-md text-sm font-medium"
          >
            Back to Assignments
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <nav className="flex mb-8" aria-label="Breadcrumb">
        <ol className="inline-flex items-center space-x-1 md:space-x-3">
          <li className="inline-flex items-center">
            <Link
              href="/assignments"
              className="inline-flex items-center text-sm font-medium text-gray-700 hover:text-primary-600"
            >
              <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z" />
              </svg>
              Assignments
            </Link>
          </li>
          <li>
            <div className="flex items-center">
              <svg className="w-6 h-6 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
              </svg>
              <span className="ml-1 text-sm font-medium text-gray-500 md:ml-2 truncate max-w-xs">
                {assignment.title}
              </span>
            </div>
          </li>
        </ol>
      </nav>

      {/* Assignment Details */}
      <AssignmentDetails assignment={assignment} />

      {/* Attachments */}
      {assignment.attachments && assignment.attachments.length > 0 && (
        <AttachmentsList attachments={assignment.attachments} />
      )}

      {/* Solution */}
      {solution ? (
        <SolutionView 
          solution={solution} 
          onRegenerate={handleRegenerateSolution}
          isRegenerating={regenerating}
        />
      ) : (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 mt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-white">
                  {assignment.status === 'processing' ? 'Solution in Progress' : assignment.status === 'completed' ? 'Solution Ready' : assignment.status === 'failed' ? 'Solution Generation Failed' : 'No Solution Yet'}
                </h3>
                <div className="mt-2 text-sm text-gray-300">
                  <p>
                    {assignment.status === 'processing'
                      ? 'Our AI is currently working on generating a solution for this assignment. Please check back in a few minutes.'
                      : assignment.status === 'completed'
                      ? 'A solution has been generated. Click the button below to view it.'
                      : assignment.status === 'failed'
                      ? 'There was an error generating the solution. Please try again.'
                      : 'Click the button below to generate an AI-powered solution for this assignment.'}
                  </p>
                </div>
                {solveMessage && (
                  <p className={`mt-2 text-sm ${solveMessage.startsWith('✓') ? 'text-green-400' : 'text-red-400'}`}>
                    {solveMessage}
                  </p>
                )}
              </div>
            </div>
            {assignment.status === 'completed' ? (
              <button
                onClick={async () => {
                  try {
                    setError(null)
                    const { apiClient } = await import('@/lib/api')
                    console.log('Fetching solution for:', assignmentId)
                    const solutionResponse = await apiClient.getSolution(assignmentId)
                    console.log('Solution received:', solutionResponse)
                    setSolution(solutionResponse)
                  } catch (err: any) {
                    console.error('Error fetching solution:', err)
                    console.error('Error details:', {
                      message: err?.message,
                      status: err?.status,
                      code: err?.code
                    })
                    setError(`Failed to load solution: ${err?.message || 'Unknown error'}. Please check browser console for details.`)
                  }
                }}
                className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                View Solution
              </button>
            ) : assignment.status !== 'processing' ? (
              <>
                <button
                  onClick={assignment.status === 'failed' ? handleRegenerateSolution : handleSolveAssignment}
                  disabled={solving}
                  className="ml-4 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white rounded-md text-sm font-medium flex items-center gap-2"
                >
                  {solving ? (
                    <>
                      <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      {assignment.status === 'failed' ? 'Retrying...' : 'Solving...'}
                    </>
                  ) : (
                    <>
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      {assignment.status === 'failed' ? 'Retry with AI' : 'Solve with AI'}
                    </>
                  )}
                </button>
                {assignment.status === 'failed' && (
                  <span className="ml-2 text-xs text-gray-400">(Previous attempt failed)</span>
                )}
              </>
            ) : (
              <button
                onClick={async () => {
                  if (confirm('This assignment appears stuck in processing. Reset it to try again?')) {
                    try {
                      const { apiClient } = await import('@/lib/api')
                      await apiClient.resetAssignmentStatus(assignmentId)
                      // Refresh the page
                      window.location.reload()
                    } catch (err: any) {
                      setError(`Failed to reset: ${err?.message || 'Unknown error'}`)
                    }
                  }
                }}
                className="ml-4 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-md text-sm font-medium flex items-center gap-2"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Reset Status
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}