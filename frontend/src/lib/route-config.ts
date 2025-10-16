// frontend/src/lib/route-config.ts

/**
 * Route configuration for authentication and access control
 *
 * Strategy:
 * 1. Pattern-based detection (default)
 * 2. Explicit configuration (override)
 */

export interface RouteConfig {
  /** Routes that explicitly require authentication */
  protected: string[]
  /** Routes that explicitly do NOT require authentication */
  public: string[]
}

/**
 * Route configuration
 * Only list exceptions - most routes follow pattern-based detection
 */
export const routeConfig: RouteConfig = {
  // Protected routes (require authentication)
  protected: [
    '/dashboard',
    '/documents',
    '/categories',
    '/settings',
    '/profile',
    '/upload'
  ],

  // Public routes (do not require authentication)
  public: [
    '/',
    '/about',
    '/features',
    '/pricing',
    '/contact',
    '/login',
    '/legal'
  ]
}

/**
 * Determine if a route requires authentication
 *
 * Logic:
 * 1. Check explicit public routes
 * 2. Check explicit protected routes
 * 3. Pattern-based detection (default to protected for unknown routes)
 */
export function isProtectedRoute(pathname: string): boolean {
  // Exact match or prefix match for public routes
  const isPublic = routeConfig.public.some(route =>
    pathname === route || pathname.startsWith(route + '/')
  )

  if (isPublic) {
    return false
  }

  // Exact match or prefix match for protected routes
  const isProtected = routeConfig.protected.some(route =>
    pathname === route || pathname.startsWith(route + '/')
  )

  if (isProtected) {
    return true
  }

  // Pattern-based detection for unknown routes
  // Public patterns: /legal/*, /blog/*, API docs, etc.
  const publicPatterns = [
    /^\/legal\/.*/,
    /^\/blog\/.*/,
    /^\/docs\/.*/,
    /^\/api-docs.*/,
    /^\/help\/.*/,
    /^\/careers.*/,
    /^\/integrations.*/,
    /^\/security.*/
  ]

  if (publicPatterns.some(pattern => pattern.test(pathname))) {
    return false
  }

  // Default: unknown routes are protected (fail-safe)
  return true
}

/**
 * Get route metadata for debugging/logging
 */
export function getRouteMetadata(pathname: string) {
  return {
    pathname,
    isProtected: isProtectedRoute(pathname),
    requiresAuth: isProtectedRoute(pathname)
  }
}
