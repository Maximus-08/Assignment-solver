'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import AssignmentList from '@/components/assignments/AssignmentList'
import SearchAndFilter from '@/components/assignments/SearchAndFilter'
import { apiClient } from '@/lib/api'
import { assignmentKeys } from '@/hooks/useAssignments'

export default function AssignmentsPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSubject, setSelectedSubject] = useState('')
  const [sortBy, setSortBy] = useState('upload_date')
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncMessage, setSyncMessage] = useState('')

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin')
    }
  }, [status, router])

  const handleSync = async () => {
    setIsSyncing(true)
    setSyncMessage('')
    
    try {
      const response = await apiClient.syncGoogleClassroom()
      console.log('Sync response:', response)
      // The backend returns data directly, not wrapped in a data property
      const result = response.data || response
      
      // Invalidate and refetch all assignment queries
      await queryClient.invalidateQueries({ 
        queryKey: assignmentKeys.all,
        refetchType: 'all'
      })
      // Force immediate refetch of active queries
      await queryClient.refetchQueries({ 
        queryKey: assignmentKeys.all 
      })
      
      setSyncMessage(
        `✓ Synced ${result.synced} new assignments from ${result.total_courses} courses (${result.skipped} skipped)`
      )
    } catch (error: any) {
      console.error('Sync failed - Full error:', error)
      console.error('Error message:', error?.message)
      console.error('Error details:', error?.details)
      const errorMsg = error?.message || error?.details || JSON.stringify(error) || 'Unknown error'
      setSyncMessage(`✗ Sync failed: ${errorMsg}`)
    } finally {
      setIsSyncing(false)
    }
  }

  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!session) {
    return null
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-white">Your Assignments</h1>
          <p className="text-gray-300 mt-2">
            Browse and search through your assignment solutions
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSyncing ? (
              <>
                <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Syncing...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Sync Google Classroom
              </>
            )}
          </button>
          {syncMessage && (
            <p className={`text-sm ${syncMessage.startsWith('✓') ? 'text-green-400' : 'text-red-400'}`}>
              {syncMessage}
            </p>
          )}
        </div>
      </div>

      <SearchAndFilter
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedSubject={selectedSubject}
        onSubjectChange={setSelectedSubject}
        sortBy={sortBy}
        onSortChange={setSortBy}
      />

      <AssignmentList
        searchQuery={searchQuery}
        selectedSubject={selectedSubject}
        sortBy={sortBy}
      />
    </div>
  )
}