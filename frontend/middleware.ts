// frontend/middleware.ts
/**
 * Next.js Middleware for authentication and security
 *
 * AUTHENTICATION ARCHITECTURE (Updated October 26, 2025):
 * - Backend sets cookies with Domain=.bonidoc.com (accessible across subdomains)
 * - Middleware checks for access_token cookie presence on protected routes
 * - If no token: redirect to login
 * - If token exists: allow through (backend validates JWT on API calls)
 * - This provides instant UX (no loading states) while maintaining security
 *
 * Security Model:
 * - Cookie presence check = UX optimization (prevents unnecessary renders)
 * - JWT validation = security enforcement (happens on backend API)
 * - httpOnly cookies = XSS protection (JavaScript cannot access)
 * - SameSite=Lax/Strict = CSRF protection
 */

import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Protected routes that require authentication
const PROTECTED_PATHS = ['/dashboard', '/documents', '/settings', '/categories', '/profile']

// OAuth callback routes that should be accessible even if session expired
// Backend API endpoints handle authentication, these routes just process redirects
const OAUTH_CALLBACK_PATHS = ['/settings/drive/callback']

function isProtectedRoute(pathname: string): boolean {
  // Exclude OAuth callbacks from auth check
  if (OAUTH_CALLBACK_PATHS.some(path => pathname.startsWith(path))) {
    return false
  }
  return PROTECTED_PATHS.some(path => pathname.startsWith(path))
}

interface SecurityConfig {
  enableCSP: boolean
  enableHSTS: boolean
  enableReferrerPolicy: boolean
  maxAge: number
}

const SECURITY_CONFIG: SecurityConfig = {
  enableCSP: true,
  enableHSTS: true,
  enableReferrerPolicy: true,
  maxAge: 31536000
}

function addSecurityHeaders(response: NextResponse, request: NextRequest): NextResponse {
  const headers = response.headers

  if (SECURITY_CONFIG.enableCSP) {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL

    const cspDirectives = [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com https://apis.google.com",
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
      "font-src 'self' https://fonts.gstatic.com",
      "img-src 'self' data: https: blob:",
      `connect-src 'self' ${apiUrl} https://accounts.google.com https://www.googleapis.com`,
      "frame-src 'self' https://accounts.google.com",
      "form-action 'self'",
      "base-uri 'self'",
      "object-src 'none'"
    ]
    headers.set('Content-Security-Policy', cspDirectives.join('; '))
  }

  if (SECURITY_CONFIG.enableHSTS && request.nextUrl.protocol === 'https:') {
    headers.set(
      'Strict-Transport-Security',
      `max-age=${SECURITY_CONFIG.maxAge}; includeSubDomains; preload`
    )
  }

  headers.set('X-Content-Type-Options', 'nosniff')
  headers.set('X-Frame-Options', 'DENY')
  headers.set('X-XSS-Protection', '1; mode=block')
  headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')

  if (SECURITY_CONFIG.enableReferrerPolicy) {
    headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  }

  return response
}

function addPerformanceHeaders(response: NextResponse, request: NextRequest): NextResponse {
  const requestId = crypto.randomUUID()
  response.headers.set('X-Request-ID', requestId)

  const { pathname } = request.nextUrl
  if (pathname.startsWith('/_next/static/') || pathname.match(/\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2)$/)) {
    response.headers.set('Cache-Control', 'public, max-age=31536000, immutable')
  }

  return response
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Skip processing for Next.js internals and static assets
  if (
    pathname.startsWith('/_next/') ||
    pathname.startsWith('/favicon.ico') ||
    pathname.match(/\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2)$/)
  ) {
    const response = NextResponse.next()
    return addPerformanceHeaders(addSecurityHeaders(response, request), request)
  }

  // Authentication check for protected routes
  if (isProtectedRoute(pathname)) {
    const accessToken = request.cookies.get('access_token')

    // No access token → redirect to login
    if (!accessToken) {
      const loginUrl = new URL('/login', request.url)
      loginUrl.searchParams.set('redirect', pathname)
      console.log(`[Middleware] No access_token, redirecting to login. Path: ${pathname}`)
      return NextResponse.redirect(loginUrl)
    }

    // Access token exists → allow through
    // Note: JWT validation happens on backend API calls, not here
    console.log(`[Middleware] Access token found, allowing access to: ${pathname}`)
  }

  // All other requests: apply security headers
  const response = NextResponse.next()
  return addPerformanceHeaders(addSecurityHeaders(response, request), request)
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'
  ]
}
