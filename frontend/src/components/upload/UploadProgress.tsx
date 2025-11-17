interface UploadProgressProps {
  progress: number
  status: 'uploading' | 'processing'
  fileName?: string
}

export default function UploadProgress({ progress, status, fileName }: UploadProgressProps) {
  const getStatusInfo = () => {
    switch (status) {
      case 'uploading':
        return {
          title: 'Uploading Files',
          description: fileName ? `Uploading ${fileName}...` : 'Uploading your files...',
          icon: (
            <svg className="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          ),
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          progressColor: 'bg-blue-600',
        }
      case 'processing':
        return {
          title: 'Processing Assignment',
          description: 'Our AI is analyzing your assignment and generating solutions...',
          icon: (
            <svg className="animate-pulse h-5 w-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          ),
          bgColor: 'bg-purple-50',
          borderColor: 'border-purple-200',
          progressColor: 'bg-purple-600',
        }
      default:
        return {
          title: 'Processing',
          description: 'Please wait...',
          icon: null,
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-200',
          progressColor: 'bg-gray-600',
        }
    }
  }

  const statusInfo = getStatusInfo()

  return (
    <div className={`${statusInfo.bgColor} border-b ${statusInfo.borderColor} px-6 py-4`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center">
          {statusInfo.icon}
          <div className="ml-3">
            <h3 className="text-sm font-medium text-gray-900">{statusInfo.title}</h3>
            <p className="text-sm text-gray-600">{statusInfo.description}</p>
          </div>
        </div>
        <div className="text-sm font-medium text-gray-900">
          {status === 'uploading' ? `${progress}%` : ''}
        </div>
      </div>
      
      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`${statusInfo.progressColor} h-2 rounded-full transition-all duration-300 ease-out`}
          style={{
            width: status === 'uploading' ? `${progress}%` : '100%',
            animation: status === 'processing' ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none'
          }}
        />
      </div>
      
      {status === 'processing' && (
        <div className="mt-3 flex items-center text-xs text-gray-500">
          <svg className="animate-spin h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          This may take a few moments depending on the complexity of your assignment
        </div>
      )}
    </div>
  )
}