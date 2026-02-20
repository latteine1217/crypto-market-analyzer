'use client'

import { useEffect } from 'react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Application error:', error)
  }, [error])

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] p-6 text-center">
      <div className="bg-red-500/10 p-4 rounded-full mb-6">
        <svg
          className="w-12 h-12 text-red-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </div>
      <h2 className="text-2xl font-bold mb-4 text-white">Something went wrong!</h2>
      <p className="text-gray-400 mb-8 max-w-md">
        An unexpected error occurred in the application. We have been notified and are working to fix it.
      </p>
      <div className="flex gap-4">
        <button
          onClick={() => reset()}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors font-medium"
        >
          Try again
        </button>
        <button
          onClick={() => window.location.href = '/technical'}
          className="px-6 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-md transition-colors font-medium"
        >
          Go to Dashboard
        </button>
      </div>
      {process.env.NODE_ENV === 'development' && (
        <div className="mt-12 p-4 bg-black/50 rounded-lg text-left overflow-auto max-w-full">
          <p className="text-red-400 font-mono text-sm">{error.message}</p>
          {error.stack && (
            <pre className="mt-2 text-gray-500 font-mono text-xs whitespace-pre-wrap">
              {error.stack}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
