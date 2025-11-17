import { APIError } from './api'

export interface ErrorInfo {
  title: string
  message: string
  action?: string
  retryable: boolean
}

export function getErrorInfo(error: unknown): ErrorInfo {
  if (error instanceof APIError) {
    switch (error.status) {
      case 400:
        return {
          title: 'Invalid Request',
          message: error.message || 'The request contains invalid data. Please check your input and try again.',
          retryable: false,
        }
      case 401:
        return {
          title: 'Authentication Required',
          message: 'Please sign in to continue.',
          action: 'Sign In',
          retryable: false,
        }
      case 403:
        return {
          title: 'Access Denied',
          message: 'You don\'t have permission to perform this action.',
          retryable: false,
        }
      case 404:
        return {
          title: 'Not Found',
          message: 'The requested resource could not be found.',
          retryable: false,
        }
      case 409:
        return {
          title: 'Conflict',
          message: error.message || 'There was a conflict with the current state. Please refresh and try again.',
          retryable: true,
        }
      case 413:
        return {
          title: 'File Too Large',
          message: 'The uploaded file is too large. Please choose a smaller file.',
          retryable: false,
        }
      case 422:
        return {
          title: 'Validation Error',
          message: error.message || 'The provided data is invalid. Please check your input.',
          retryable: false,
        }
      case 429:
        return {
          title: 'Too Many Requests',
          message: 'You\'re making requests too quickly. Please wait a moment and try again.',
          retryable: true,
        }
      case 500:
        return {
          title: 'Server Error',
          message: 'An internal server error occurred. Please try again later.',
          retryable: true,
        }
      case 502:
      case 503:
      case 504:
        return {
          title: 'Service Unavailable',
          message: 'The service is temporarily unavailable. Please try again in a few minutes.',
          retryable: true,
        }
      case 0:
        return {
          title: 'Network Error',
          message: 'Unable to connect to the server. Please check your internet connection.',
          retryable: true,
        }
      default:
        return {
          title: 'Unexpected Error',
          message: error.message || 'An unexpected error occurred. Please try again.',
          retryable: true,
        }
    }
  }

  if (error instanceof Error) {
    return {
      title: 'Error',
      message: error.message,
      retryable: true,
    }
  }

  return {
    title: 'Unknown Error',
    message: 'An unknown error occurred. Please try again.',
    retryable: true,
  }
}

export function isRetryableError(error: unknown): boolean {
  return getErrorInfo(error).retryable
}

export function getRetryDelay(attemptNumber: number): number {
  // Exponential backoff with jitter
  const baseDelay = 1000 // 1 second
  const maxDelay = 30000 // 30 seconds
  const delay = Math.min(baseDelay * Math.pow(2, attemptNumber), maxDelay)
  const jitter = Math.random() * 0.1 * delay
  return delay + jitter
}