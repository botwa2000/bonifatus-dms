// frontend/middleware.ts
/**
 * Next.js Middleware for security headers and performance optimization
 *
 * AUTHENTICATION ARCHITECTURE:
 * - Authentication is enforced at the API level with httpOnly cookies
 * - Frontend pages check auth by calling /auth/me API
 * - Middleware does NOT redirect based on auth status because:
 *   1. Backend cookies are on api.bonidoc.com domain
 *   2. Frontend runs on bonidoc.com domain
 *   3. Cross-domain cookie access is blocked by browsers (security feature)
 *   4. Client-side auth checks would be manipulable
 *
 * This is the correct architecture for cross-domain SPA + API setups.
 * Security is enforced where it matters: at the API boundary with httpOnly cookies.
 */

import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

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

// No auth redirects in middleware - handled by page components
// This is the correct pattern for cross-domain authentication

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

  // All other requests: apply security headers
  const response = NextResponse.next()
  return addPerformanceHeaders(addSecurityHeaders(response, request), request)
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'
  ]
}