import { getErrorInfo } from '@/lib/errorHandling'

interface ErrorDisplayProps {
  error: unknown
  onRetry?: () => void
  onAction?: () => void
  className?: string
}

export default function ErrorDisplay({ 
  error, 
  onRetry, 
  onAction, 
  className = '' 
}: ErrorDisplayProps) {
  const errorInfo = getErrorInfo(error)

  return (
    <div className={`bg-red-50 border border-red-200 rounded-lg p-6 ${className}`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium text-red-800">
            {errorInfo.title}
          </h3>
          <div className="mt-2 text-sm text-red-700">
            <p>{errorInfo.message}</p>
          </div>
          {(onRetry || onAction) && (
            <div className="mt-4 flex space-x-3">
              {onRetry && errorInfo.retryable && (
                <button
                  onClick={onRetry}
                  className="bg-red-600 hover:bg-red-700 text-white px-3 py-1.5 rounded-md text-xs font-medium"
                >
                  Try Again
                </button>
              )}
              {onAction && errorInfo.action && (
                <button
                  onClick={onAction}
                  className="bg-white hover:bg-red-50 text-red-600 border border-red-300 px-3 py-1.5 rounded-md text-xs font-medium"
                >
                  {errorInfo.action}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}