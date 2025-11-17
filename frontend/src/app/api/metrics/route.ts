/**
 * Metrics collection endpoint for frontend performance monitoring
 */
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const metricData = await request.json()
    
    // Log metric to console (in production, this would go to a metrics service)
    console.log('Frontend Metric:', {
      name: metricData.name,
      value: metricData.value,
      timestamp: metricData.timestamp,
      url: request.headers.get('referer'),
    })

    // In production, you would send this to your metrics service
    // Example: await sendToMetricsService(metricData)

    return NextResponse.json({ success: true }, { status: 200 })
  } catch (error) {
    console.error('Failed to process metric:', error)
    return NextResponse.json(
      { error: 'Failed to process metric' },
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