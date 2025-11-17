'use client'

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import Link from 'next/link'
import { useAssignments } from '@/hooks/useAssignments'

export default function Home() {
  const { data: session, status } = useSession()
  const router = useRouter()
  
  // Fetch assignments to get stats
  const { data: assignmentsData, isLoading: loadingAssignments } = useAssignments({
    page: 1,
    limit: 100 // Get enough to count stats
  })

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin')
    }
  }, [status, router])

  // Calculate stats from assignments data
  const stats = {
    total: assignmentsData?.total || 0,
    completed: assignmentsData?.assignments?.filter(a => a.status === 'completed').length || 0,
    processing: assignmentsData?.assignments?.filter(a => a.status === 'processing').length || 0,
    pending: assignmentsData?.assignments?.filter(a => a.status === 'pending').length || 0,
  }

  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!session) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Assignment Solver
          </h1>
          <p className="text-lg text-gray-600 mb-8">
            AI-powered assignment solutions from Google Classroom
          </p>
          <Link
            href="/auth/signin"
            className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-3 rounded-md text-lg font-medium"
          >
            Get Started
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">
          Welcome back, {session.user?.name}!
        </h1>
        <p className="text-gray-300 mt-2">
          Here's your assignment dashboard
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-gray-800 rounded-lg shadow p-6 border border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-primary-900/50 rounded-lg">
              <svg className="h-6 w-6 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Total Assignments</p>
              <p className="text-2xl font-semibold text-white">
                {loadingAssignments ? '...' : stats.total}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg shadow p-6 border border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-green-900/50 rounded-lg">
              <svg className="h-6 w-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Completed</p>
              <p className="text-2xl font-semibold text-white">
                {loadingAssignments ? '...' : stats.completed}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg shadow p-6 border border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-900/50 rounded-lg">
              <svg className="h-6 w-6 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Processing</p>
              <p className="text-2xl font-semibold text-white">
                {loadingAssignments ? '...' : stats.processing}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg shadow p-6 border border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-blue-900/50 rounded-lg">
              <svg className="h-6 w-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Pending</p>
              <p className="text-2xl font-semibold text-white">
                {loadingAssignments ? '...' : stats.pending}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-gray-800 rounded-lg shadow p-6 border border-gray-700">
        <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link
            href="/upload"
            className="flex items-center p-4 border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors"
          >
            <div className="p-2 bg-primary-900/50 rounded-lg mr-4">
              <svg className="h-6 w-6 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <h3 className="font-medium text-white">Upload Assignment</h3>
              <p className="text-sm text-gray-400">Manually upload an assignment for AI solving</p>
            </div>
          </Link>

          <Link
            href="/assignments"
            className="flex items-center p-4 border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors"
          >
            <div className="p-2 bg-blue-900/50 rounded-lg mr-4">
              <svg className="h-6 w-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h3 className="font-medium text-white">View All Assignments</h3>
              <p className="text-sm text-gray-400">Browse your complete assignment library</p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  )
}