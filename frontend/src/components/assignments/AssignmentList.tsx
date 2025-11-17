'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Assignment } from '@/types'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import AssignmentCard from './AssignmentCard'
import Pagination from './Pagination'
import { useAssignments } from '@/hooks/useAssignments'

interface AssignmentListProps {
  searchQuery: string
  selectedSubject: string
  sortBy: string
}

export default function AssignmentList({
  searchQuery,
  selectedSubject,
  sortBy,
}: AssignmentListProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 12

  // Fetch assignments from backend
  const { data, isLoading, error } = useAssignments({
    page: currentPage,
    limit: itemsPerPage,
    search: searchQuery || undefined,
    subject: selectedSubject || undefined,
    sort: sortBy || undefined,
  })

  // Extract from APIResponse wrapper
  const assignments = data?.data?.assignments || []
  const totalCount = data?.data?.total || 0
  const totalPages = Math.ceil(totalCount / itemsPerPage)

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [searchQuery, selectedSubject, sortBy])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-400 mb-4">
          <svg className="w-16 h-16 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-white mb-2">Failed to Load Assignments</h3>
        <p className="text-gray-300 mb-4">
          {error instanceof Error ? error.message : 'An error occurred while fetching assignments'}
        </p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    )
  }

  if (assignments.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 mb-4">
          <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No assignments found</h3>
        <p className="text-gray-600 mb-4">
          {searchQuery || selectedSubject
            ? 'Try adjusting your search or filter criteria.'
            : 'You don\'t have any assignments yet.'}
        </p>
        <Link
          href="/upload"
          className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-md text-sm font-medium"
        >
          Upload Assignment
        </Link>
      </div>
    )
  }

  return (
    <div>
      {/* Results Summary */}
      <div className="mb-6 flex justify-between items-center">
        <p className="text-sm text-gray-600">
          Showing {assignments.length} of {totalCount} assignments
        </p>
        <div className="text-sm text-gray-500">
          Page {currentPage} of {totalPages}
        </div>
      </div>

      {/* Assignment Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {assignments.map((assignment) => (
          <AssignmentCard key={assignment.id} assignment={assignment} />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={setCurrentPage}
        />
      )}
    </div>
  )
}