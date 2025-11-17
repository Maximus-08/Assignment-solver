/**
 * Health check endpoint for frontend monitoring
 */
import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    // Basic health check
    const healthData = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      service: 'assignment-solver-frontend',
      version: '1.0.0',
      environment: process.env.NODE_ENV || 'development',
    }

    // Check backend connectivity
    let backendStatus = 'unknown'
    let backendResponseTime = null

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000'
      const startTime = Date.now()
      
      const response = await fetch(`${backendUrl}/api/v1/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        // Short timeout for health checks
        signal: AbortSignal.timeout(5000),
      })
      
      const endTime = Date.now()
      backendResponseTime = endTime - startTime
      
      if (response.ok) {
        backendStatus = 'healthy'
      } else {
        backendStatus = 'unhealthy'
      }
    } catch (error) {
      backendStatus = 'unreachable'
      console.error('Backend health check failed:', error)
    }

    const detailedHealthData = {
      ...healthData,
      checks: {
        backend: {
          status: backendStatus,
          response_time_ms: backendResponseTime,
        },
        memory: {
          // Basic memory info (if available in Node.js environment)
          usage: process.memoryUsage ? process.memoryUsage() : null,
        },
      },
    }

    // Return 503 if backend is unreachable (critical dependency)
    if (backendStatus === 'unreachable') {
      return NextResponse.json(detailedHealthData, { status: 503 })
    }

    // Return 200 for healthy or degraded states
    return NextResponse.json(detailedHealthData, { status: 200 })

  } catch (error) {
    console.error('Health check failed:', error)
    
    return NextResponse.json(
      {
        status: 'unhealthy',
        timestamp: new Date().toISOString(),
        service: 'assignment-solver-frontend',
        error: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 503 }
    )
  }
}

// Support HEAD requests for simple health checks
export async function HEAD(request: NextRequest) {
  try {
    // Simple connectivity check
    return new NextResponse(null, { status: 200 })
  } catch (error) {
    return new NextResponse(null, { status: 503 })
  }
}