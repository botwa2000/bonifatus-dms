// frontend/middleware.ts

import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

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
  maxAge: 31536000
}

function isAuthenticated(request: NextRequest): boolean {
  const hasAccessToken = request.cookies.get('access_token')?.value
  const hasAuthHeader = request.headers.get('authorization')
  const hasTokenCookie = request.cookies.get('bonifatus_has_token')?.value === 'true'
  
  return !!(hasAccessToken || hasAuthHeader || hasTokenCookie)
}

function isProtectedRoute(pathname: string): boolean {
  return PROTECTED_ROUTES.some(route => pathname.startsWith(route))
}

function isAuthRoute(pathname: string): boolean {
  return AUTH_ROUTES.some(route => pathname.startsWith(route))
}

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some(route => pathname === route)
}

function addSecurityHeaders(response: NextResponse, request: NextRequest): NextResponse {
  const headers = response.headers

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

function handleAuthRedirect(request: NextRequest, isAuth: boolean): NextResponse | null {
  const { pathname, searchParams } = request.nextUrl
  
  if (isProtectedRoute(pathname) && !isAuth) {
    console.info(`[Middleware] Redirecting unauthenticated user from ${pathname} to /login`)
    
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    
    searchParams.forEach((value, key) => {
      if (key !== 'redirect') {
        loginUrl.searchParams.set(key, value)
      }
    })
    
    return NextResponse.redirect(loginUrl)
  }

  if (isAuthRoute(pathname) && isAuth) {
    console.info(`[Middleware] Redirecting authenticated user from ${pathname} to /dashboard`)
    
    const redirectTo = searchParams.get('redirect')
    const dashboardUrl = new URL(redirectTo || '/dashboard', request.url)
    
    return NextResponse.redirect(dashboardUrl)
  }

  return null
}

function handleApiRoute(request: NextRequest): NextResponse | null {
  const { pathname } = request.nextUrl
  
  const publicApiRoutes = ['/api/health', '/api/status', '/api/auth']
  const isPublicApi = publicApiRoutes.some(route => pathname.startsWith(route))
  
  if (isPublicApi) {
    return null
  }

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
  const startTime = Date.now()
  const { pathname } = request.nextUrl
  
  console.debug(`[Middleware] Processing ${request.method} ${pathname}`)

  try {
    const apiResponse = handleApiRoute(request)
    if (apiResponse) {
      return addSecurityHeaders(apiResponse, request)
    }

    if (
      pathname.startsWith('/_next/') ||
      pathname.startsWith('/favicon.ico') ||
      pathname.includes('/api/') ||
      pathname.match(/\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2)$/)
    ) {
      const response = NextResponse.next()
      return addPerformanceHeaders(addSecurityHeaders(response, request), request)
    }

    const isAuth = isAuthenticated(request)
    
    const redirectResponse = handleAuthRedirect(request, isAuth)
    if (redirectResponse) {
      return addSecurityHeaders(redirectResponse, request)
    }

    const response = NextResponse.next()
    const finalResponse = addPerformanceHeaders(addSecurityHeaders(response, request), request)
    
    const processingTime = Date.now() - startTime
    console.debug(`[Middleware] Processed ${pathname} in ${processingTime}ms`)
    
    return finalResponse

  } catch (error) {
    console.error('[Middleware] Unexpected error:', error)
    
    const errorResponse = NextResponse.redirect(new URL('/', request.url))
    return addSecurityHeaders(errorResponse, request)
  }
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'
  ]
}