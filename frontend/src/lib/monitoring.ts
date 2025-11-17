/**
 * Frontend monitoring and error tracking utilities
 */

// Error tracking service
class ErrorTracker {
  private static instance: ErrorTracker
  private isInitialized = false

  static getInstance(): ErrorTracker {
    if (!ErrorTracker.instance) {
      ErrorTracker.instance = new ErrorTracker()
    }
    return ErrorTracker.instance
  }

  initialize() {
    if (this.isInitialized) return

    // Initialize Sentry if DSN is provided
    if (process.env.SENTRY_DSN) {
      this.initializeSentry()
    }

    // Set up global error handlers
    this.setupGlobalErrorHandlers()
    
    this.isInitialized = true
  }

  private async initializeSentry() {
    try {
      // Only initialize if Sentry DSN is provided
      if (!process.env.SENTRY_DSN) {
        console.log('Sentry DSN not provided, skipping Sentry initialization')
        return
      }
      
      // @ts-ignore - Sentry is optional dependency
      const Sentry = await import('@sentry/nextjs')
      
      Sentry.init({
        dsn: process.env.SENTRY_DSN,
        environment: process.env.NODE_ENV,
        tracesSampleRate: 0.1,
        debug: process.env.NODE_ENV === 'development',
        
        // Performance monitoring
        integrations: [
          new Sentry.BrowserTracing({
            tracePropagationTargets: [
              'localhost',
              process.env.NEXT_PUBLIC_BACKEND_API_URL || '',
            ],
          }),
        ],

        // Filter out common non-critical errors
        beforeSend(event: any) {
          // Filter out network errors that are not actionable
          if (event.exception?.values?.[0]?.type === 'NetworkError') {
            return null
          }
          
          // Filter out cancelled requests
          if (event.exception?.values?.[0]?.value?.includes('AbortError')) {
            return null
          }
          
          return event
        },
      })
    } catch (error) {
      console.warn('Failed to initialize Sentry (optional dependency):', error)
    }
  }

  private setupGlobalErrorHandlers() {
    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      console.error('Unhandled promise rejection:', event.reason)
      this.captureError(event.reason, {
        type: 'unhandled_promise_rejection',
        promise: event.promise,
      })
    })

    // Handle global errors
    window.addEventListener('error', (event) => {
      console.error('Global error:', event.error)
      this.captureError(event.error, {
        type: 'global_error',
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      })
    })
  }

  captureError(error: Error | string, context?: Record<string, any>) {
    console.error('Captured error:', error, context)

    // Send to Sentry if available
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      const Sentry = (window as any).Sentry
      Sentry.withScope((scope: any) => {
        if (context) {
          Object.keys(context).forEach(key => {
            scope.setTag(key, context[key])
          })
        }
        Sentry.captureException(error)
      })
    }

    // Send to custom error endpoint
    this.sendToErrorEndpoint(error, context)
  }

  private async sendToErrorEndpoint(error: Error | string, context?: Record<string, any>) {
    try {
      await fetch('/api/errors', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          error: error instanceof Error ? {
            message: error.message,
            stack: error.stack,
            name: error.name,
          } : { message: error },
          context,
          timestamp: new Date().toISOString(),
          url: window.location.href,
          userAgent: navigator.userAgent,
        }),
      })
    } catch (err) {
      console.warn('Failed to send error to endpoint:', err)
    }
  }

  captureMessage(message: string, level: 'info' | 'warning' | 'error' = 'info') {
    console.log(`[${level.toUpperCase()}] ${message}`)

    if (typeof window !== 'undefined' && (window as any).Sentry) {
      const Sentry = (window as any).Sentry
      Sentry.captureMessage(message, level)
    }
  }

  setUser(user: { id: string; email?: string; name?: string }) {
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      const Sentry = (window as any).Sentry
      Sentry.setUser(user)
    }
  }

  addBreadcrumb(message: string, category: string, data?: Record<string, any>) {
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      const Sentry = (window as any).Sentry
      Sentry.addBreadcrumb({
        message,
        category,
        data,
        timestamp: Date.now() / 1000,
      })
    }
  }
}

// Performance monitoring
class PerformanceMonitor {
  private static instance: PerformanceMonitor
  private metrics: Map<string, number> = new Map()

  static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor()
    }
    return PerformanceMonitor.instance
  }

  startTiming(name: string) {
    this.metrics.set(name, performance.now())
  }

  endTiming(name: string): number {
    const startTime = this.metrics.get(name)
    if (!startTime) {
      console.warn(`No start time found for metric: ${name}`)
      return 0
    }

    const duration = performance.now() - startTime
    this.metrics.delete(name)

    // Log slow operations
    if (duration > 1000) {
      console.warn(`Slow operation detected: ${name} took ${duration.toFixed(2)}ms`)
      ErrorTracker.getInstance().captureMessage(
        `Slow operation: ${name} (${duration.toFixed(2)}ms)`,
        'warning'
      )
    }

    return duration
  }

  measureAsync<T>(name: string, fn: () => Promise<T>): Promise<T> {
    this.startTiming(name)
    return fn().finally(() => {
      this.endTiming(name)
    })
  }

  measureSync<T>(name: string, fn: () => T): T {
    this.startTiming(name)
    try {
      return fn()
    } finally {
      this.endTiming(name)
    }
  }

  // Web Vitals monitoring
  observeWebVitals() {
    if (typeof window === 'undefined') return

    // Observe Core Web Vitals
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const anyEntry = entry as any
        const metric = {
          name: entry.name,
          value: anyEntry.value || anyEntry.processingStart - entry.startTime,
          timestamp: Date.now(),
        }

        console.log('Web Vital:', metric)
        
        // Send to analytics
        this.sendMetric(metric)
      }
    })

    // Observe different types of performance entries
    try {
      observer.observe({ entryTypes: ['navigation', 'paint', 'largest-contentful-paint'] })
    } catch (error) {
      console.warn('Performance observer not supported:', error)
    }
  }

  private async sendMetric(metric: { name: string; value: number; timestamp: number }) {
    try {
      await fetch('/api/metrics', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(metric),
      })
    } catch (error) {
      console.warn('Failed to send metric:', error)
    }
  }
}

// API monitoring
export class APIMonitor {
  private static instance: APIMonitor

  static getInstance(): APIMonitor {
    if (!APIMonitor.instance) {
      APIMonitor.instance = new APIMonitor()
    }
    return APIMonitor.instance
  }

  async monitorRequest<T>(
    name: string,
    request: () => Promise<T>,
    options?: {
      expectedDuration?: number
      retries?: number
    }
  ): Promise<T> {
    const startTime = performance.now()
    const errorTracker = ErrorTracker.getInstance()
    
    errorTracker.addBreadcrumb(`API request started: ${name}`, 'api')

    try {
      const result = await request()
      const duration = performance.now() - startTime

      // Log successful request
      console.log(`API request completed: ${name} (${duration.toFixed(2)}ms)`)
      
      // Check if request was slower than expected
      if (options?.expectedDuration && duration > options.expectedDuration) {
        errorTracker.captureMessage(
          `Slow API request: ${name} took ${duration.toFixed(2)}ms (expected < ${options.expectedDuration}ms)`,
          'warning'
        )
      }

      errorTracker.addBreadcrumb(`API request completed: ${name}`, 'api', {
        duration: duration.toFixed(2),
        status: 'success',
      })

      return result
    } catch (error) {
      const duration = performance.now() - startTime
      
      console.error(`API request failed: ${name} (${duration.toFixed(2)}ms)`, error)
      
      errorTracker.addBreadcrumb(`API request failed: ${name}`, 'api', {
        duration: duration.toFixed(2),
        status: 'error',
        error: error instanceof Error ? error.message : String(error),
      })

      errorTracker.captureError(error instanceof Error ? error : new Error(String(error)), {
        api_request: name,
        duration: duration.toFixed(2),
      })

      throw error
    }
  }
}

// Initialize monitoring
export function initializeMonitoring() {
  if (typeof window === 'undefined') return

  const errorTracker = ErrorTracker.getInstance()
  const performanceMonitor = PerformanceMonitor.getInstance()

  errorTracker.initialize()
  performanceMonitor.observeWebVitals()

  console.log('Frontend monitoring initialized')
}

// Export singleton instances
export const errorTracker = ErrorTracker.getInstance()
export const performanceMonitor = PerformanceMonitor.getInstance()
export const apiMonitor = APIMonitor.getInstance()