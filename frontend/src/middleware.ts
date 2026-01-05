import { withAuth } from 'next-auth/middleware'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Simplified middleware without withAuth to test deployment
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  
  // Allow all routes during testing
  // TODO: Re-enable auth protection after deployment works
  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     * - api/health (health check endpoint)
     */
    '/((?!_next/static|_next/image|favicon.ico|public|api/health).*)',
  ],
}