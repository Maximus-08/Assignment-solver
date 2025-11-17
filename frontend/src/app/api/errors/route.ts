/**
 * Error collection endpoint for frontend error tracking
 */
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const errorData = await request.json()
    
    // Log error to console (in production, this would go to a logging service)
    console.error('Frontend Error:', {
      timestamp: errorData.timestamp,
      url: errorData.url,
      error: errorData.error,
      context: errorData.context,
      userAgent: errorData.userAgent,
    })

    // In production, you would send this to your logging service
    // Example: await sendToLoggingService(errorData)

    return NextResponse.json({ success: true }, { status: 200 })
  } catch (error) {
    console.error('Failed to process error report:', error)
    return NextResponse.json(
      { error: 'Failed to process error report' },
      { status: 500 }
    )
  }
}

// Handle preflight requests
export async function OPTIONS(request: NextRequest) {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  })
}