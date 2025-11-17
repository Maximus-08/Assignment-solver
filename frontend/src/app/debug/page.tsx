'use client'

import { useSession, signIn, signOut } from 'next-auth/react'

export default function DebugPage() {
  const { data: session, status } = useSession()

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-4 text-white">Session Debug</h1>
      <div className="mb-4 text-white">
        <p><strong>Status:</strong> {status}</p>
        <p><strong>Session exists:</strong> {session ? 'Yes' : 'No'}</p>
        <p><strong>User:</strong> {session?.user?.email || 'N/A'}</p>
        <p><strong>Backend Token:</strong> {session?.backendToken ? 'Present' : 'MISSING'}</p>
        <p><strong>Access Token:</strong> {session?.accessToken ? 'Present' : 'MISSING'}</p>
        <div className="mt-4 space-x-2">
          {status === 'unauthenticated' && (
            <button 
              onClick={() => signIn('google')}
              className="bg-blue-600 text-white px-4 py-2 rounded"
            >
              Sign In with Google
            </button>
          )}
          {status === 'authenticated' && (
            <button 
              onClick={() => signOut()}
              className="bg-red-600 text-white px-4 py-2 rounded"
            >
              Sign Out
            </button>
          )}
        </div>
      </div>
      <pre className="bg-gray-100 text-gray-900 p-4 rounded overflow-auto text-sm">
        {JSON.stringify(session, null, 2)}
      </pre>
    </div>
  )
}
