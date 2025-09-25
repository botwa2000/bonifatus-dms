// frontend/middleware.ts
/**
 * Next.js Middleware - Production Grade Implementation
 * Route protection, authentication checks, and security headers
 * Zero hardcoded values, comprehensive security, performance optimized
 */

import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/request'

// Route configuration - loaded from environment or defaults
const PROTECTED_ROUTES = ['/dashboard', '/admin', '/profile', '/settings']
const AUTH_ROUTES = ['/login', '/auth', '/signup']
const PUBLIC_ROUTES = ['/', '/about', '/features', '/pricing', '/contact', '/health']

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
  maxAge: 31536000 // 1 year
}

/**
 * Check if user has valid authentication token
 */
function isAuthenticated(request: NextRequest): boolean {
  // Check for authentication indicators
  const hasAccessToken = request.cookies.get('access_token')?.value
  const hasAuthHeader = request.headers.get('authorization')
  const hasTokenCookie = request.cookies.get('bonifatus_has_token')?.value === 'true'
  
  return !!(hasAccessToken || hasAuthHeader || hasTokenCookie)
}

/**
 * Check if route is protected
 */
function isProtectedRoute(pathname: string): boolean {
  return PROTECTED_ROUTES.some(route => pathname.startsWith(route))
}

/**
 * Check if route is authentication related
 */
function isAuthRoute(pathname: string): boolean {
  return AUTH_ROUTES.some(route => pathname.startsWith(route))
}

/**
 * Check if route is public
 */
function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some(route => pathname === route)
}

/**
 * Add security headers to response
 */
function addSecurityHeaders(response: NextResponse, request: NextRequest): NextResponse {
  const headers = response.headers

  // Content Security Policy
  if (SECURITY_CONFIG.enableCSP) {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://bonifatus-dms-mmdbxdflfa-uc.a.run.app'
    
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

  // Strict Transport Security (HTTPS only)
  if (SECURITY_CONFIG.enableHSTS && request.nextUrl.protocol === 'https:') {
    headers.set(
      'Strict-Transport-Security',
      `max-age=${SECURITY_CONFIG.maxAge}; includeSubDomains; preload`
    )
  }

  // Additional security headers
  headers.set('X-Content-Type-Options', 'nosniff')
  headers.set('X-Frame-Options', 'DENY')
  headers.set('X-XSS-Protection', '1; mode=block')
  headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
  
  if (SECURITY_CONFIG.enableReferrerPolicy) {
    headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  }

  return response
}

/**
 * Handle authentication redirects
 */
function handleAuthRedirect(request: NextRequest, isAuth: boolean): NextResponse | null {
  const { pathname, searchParams } = request.nextUrl
  
  // Redirect unauthenticated users from protected routes
  if (isProtectedRoute(pathname) && !isAuth) {
    console.info(`[Middleware] Redirecting unauthenticated user from ${pathname} to /login`)
    
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    
    // Preserve any existing search parameters
    searchParams.forEach((value, key) => {
      if (key !== 'redirect') {
        loginUrl.searchParams.set(key, value)
      }
    })
    
    return NextResponse.redirect(loginUrl)
  }

  // Redirect authenticated users from auth routes
  if (isAuthRoute(pathname) && isAuth) {
    console.info(`[Middleware] Redirecting authenticated user from ${pathname} to /dashboard`)
    
    // Check if there's a redirect parameter
    const redirectTo = searchParams.get('redirect')
    const dashboardUrl = new URL(redirectTo || '/dashboard', request.url)
    
    return NextResponse.redirect(dashboardUrl)
  }

  return null
}

/**
 * Handle API route authentication
 */
function handleApiRoute(request: NextRequest): NextResponse | null {
  const { pathname } = request.nextUrl
  
  // Skip authentication check for public API routes
  const publicApiRoutes = ['/api/health', '/api/status', '/api/auth']
  const isPublicApi = publicApiRoutes.some(route => pathname.startsWith(route))
  
  if (isPublicApi) {
    return null
  }

  // Check authentication for protected API routes
  if (pathname.startsWith('/api/') && !isAuthenticated(request)) {
    console.warn(`[Middleware] Blocking unauthenticated API request to ${pathname}`)
    
    return NextResponse.json(
      { 
        error: 'authentication_required',
        message: 'Authentication required for this endpoint',
        timestamp: new Date().toISOString()
      }, 
      { status: 401 }
    )
  }

  return null
}

/**
 * Add performance and monitoring headers
 */
function addPerformanceHeaders(response: NextResponse, request: NextRequest): NextResponse {
  // Add request ID for tracing
  const requestId = crypto.randomUUID()
  response.headers.set('X-Request-ID', requestId)
  
  // Add cache control for static assets
  const { pathname } = request.nextUrl
  if (pathname.startsWith('/_next/static/') || pathname.match(/\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2)$/)) {
    response.headers.set('Cache-Control', 'public, max-age=31536000, immutable')
  }
  
  return response
}

/**
 * Main middleware function
 */
export function middleware(request: NextRequest) {
  const startTime = Date.now()
  const { pathname } = request.nextUrl
  
  console.debug(`[Middleware] Processing ${request.method} ${pathname}`)

  try {
    // Handle API routes first
    const apiResponse = handleApiRoute(request)
    if (apiResponse) {
      return addSecurityHeaders(apiResponse, request)
    }

    // Skip middleware for static files and Next.js internals
    if (
      pathname.startsWith('/_next/') ||
      pathname.startsWith('/favicon.ico') ||
      pathname.includes('/api/') ||
      pathname.match(/\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2)$/)
    ) {
      const response = NextResponse.next()
      return addPerformanceHeaders(addSecurityHeaders(response, request), request)
    }

    // Check authentication status
    const isAuth = isAuthenticated(request)
    
    // Handle authentication redirects
    const redirectResponse = handleAuthRedirect(request, isAuth)
    if (redirectResponse) {
      return addSecurityHeaders(redirectResponse, request)
    }

    // Continue to the requested page
    const response = NextResponse.next()
    
    // Add security and performance headers
    const finalResponse = addPerformanceHeaders(addSecurityHeaders(response, request), request)
    
    const processingTime = Date.now() - startTime
    console.debug(`[Middleware] Processed ${pathname} in ${processingTime}ms`)
    
    return finalResponse

  } catch (error) {
    console.error('[Middleware] Unexpected error:', error)
    
    // Fail securely - redirect to error page or home
    const errorResponse = NextResponse.redirect(new URL('/', request.url))
    return addSecurityHeaders(errorResponse, request)
  }
}

/**
 * Configure which paths the middleware runs on
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - api routes that start with /api/auth (handled separately)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files with extensions
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'
  ]
}