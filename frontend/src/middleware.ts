import { withAuth } from 'next-auth/middleware'

export default withAuth(
  function middleware(req) {
    // Add any additional middleware logic here
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        // Protect all routes except auth pages and home
        const { pathname } = req.nextUrl
        
        // Allow access to these pages without authentication
        if (
          pathname.startsWith('/auth') ||
          pathname === '/' ||
          pathname.startsWith('/api/auth') ||
          pathname.startsWith('/api/health') ||
          pathname.startsWith('/_next') ||
          pathname.startsWith('/favicon.ico')
        ) {
          return true
        }
        
        // Require authentication for all other routes
        return !!token
      },
    },
  }
)

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