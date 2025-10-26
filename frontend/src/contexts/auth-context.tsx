// frontend/src/contexts/auth-context.tsx
'use client'

import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react'
import { usePathname } from 'next/navigation'
import { authService } from '@/services/auth.service'
import { User } from '@/types/auth.types'
import { isProtectedRoute } from '@/lib/route-config'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  initializeGoogleAuth: () => Promise<void>
  logout: () => Promise<void>
  clearError: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  // Initialize state from sessionStorage synchronously
  const getInitialUser = () => {
    if (typeof window === 'undefined') return null
    try {
      const stored = sessionStorage.getItem('user')
      const parsed = stored ? JSON.parse(stored) : null
      if (parsed) {
        console.log('[AuthProvider] Initial sync load:', parsed.email)
      }
      return parsed
    } catch {
      return null
    }
  }

  const initialUser = getInitialUser()

  const [user, setUser] = useState<User | null>(initialUser)
  const [isAuthenticated, setIsAuthenticated] = useState(!!initialUser)
  const [isLoading, setIsLoading] = useState(isProtectedRoute(pathname || '/') && !initialUser)
  const [error, setError] = useState<string | null>(null)
  const initializedRef = useRef(false)
  const mountedRef = useRef(true)

  // Re-check sessionStorage when navigating to protected routes
  // This handles the case where OAuth completes and saves to sessionStorage while AuthContext is already mounted
  useEffect(() => {
    const currentPath = pathname || '/'

    console.log('[AuthContext] Path changed:', {
      pathname: currentPath,
      isProtected: isProtectedRoute(currentPath),
      hasUser: !!user,
      initialized: initializedRef.current
    })

    // Skip auth check for public routes
    if (!isProtectedRoute(currentPath)) {
      console.log('[AuthContext] Public route, no action needed')
      return
    }

    // CRITICAL: Re-check sessionStorage on every protected route navigation
    // This catches OAuth completions that happened while AuthContext was already mounted
    const cachedUser = typeof window !== 'undefined' ? sessionStorage.getItem('user') : null

    if (cachedUser && !user) {
      try {
        const userData = JSON.parse(cachedUser)
        console.log('[AuthContext] Found new user in sessionStorage after navigation:', userData.email)
        setUser(userData)
        setIsAuthenticated(true)
        setIsLoading(false)
        initializedRef.current = true
        return
      } catch (error) {
        console.error('[AuthContext] Failed to parse cached user:', error)
        sessionStorage.removeItem('user')
      }
    }

    // If we already have a user, just do background refresh
    if (user) {
      console.log('[AuthContext] User already loaded, doing background refresh')

      if (!initializedRef.current) {
        initializedRef.current = true

        // Background refresh to validate session (non-blocking)
        authService.getCurrentUser().catch(() => {
          console.log('[AuthContext] Background refresh failed, clearing user')
          if (mountedRef.current) {
            setUser(null)
            setIsAuthenticated(false)
            sessionStorage.removeItem('user')
          }
        })
      }
      return
    }

    // No user in sessionStorage - check API (only for first-time visits)
    if (!initializedRef.current) {
      console.log('[AuthContext] No cached user, checking API')
      setIsLoading(true)
      initializedRef.current = true

      authService.getCurrentUser()
        .then(currentUser => {
          if (mountedRef.current) {
            console.log('[AuthContext] API returned user:', currentUser?.email || 'null')
            setUser(currentUser)
            setIsAuthenticated(!!currentUser)
            setIsLoading(false)
          }
        })
        .catch(error => {
          console.log('[AuthContext] API check failed:', error)
          if (mountedRef.current) {
            setUser(null)
            setIsAuthenticated(false)
            setIsLoading(false)
          }
        })
    }

    return () => {
      mountedRef.current = false
    }
  }, [pathname, user])

  const initializeGoogleAuth = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      await authService.initializeGoogleOAuth()
    } catch (err) {
      console.error('[AuthProvider] Google auth failed:', err)
      setError(err instanceof Error ? err.message : 'Authentication failed')
      setIsLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await authService.logout()
      setUser(null)
      setIsAuthenticated(false)
      window.location.href = '/'
    } catch (err) {
      console.error('[AuthProvider] Logout failed:', err)
      setUser(null)
      setIsAuthenticated(false)
      window.location.href = '/'
    }
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated,
      isLoading,
      error,
      initializeGoogleAuth,
      logout,
      clearError
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}