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

  // Initialize state from sessionStorage synchronously (more secure than localStorage)
  const getInitialUser = () => {
    if (typeof window === 'undefined') return null
    try {
      const stored = sessionStorage.getItem('user')
      return stored ? JSON.parse(stored) : null
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

  useEffect(() => {
    const initialize = async () => {
      const currentPath = pathname || '/'

      console.log('[AuthContext] Initialize called:', {
        pathname: currentPath,
        isProtected: isProtectedRoute(currentPath),
        hasUser: !!user,
        initialized: initializedRef.current
      })

      if (!isProtectedRoute(currentPath)) {
        console.log('[AuthContext] Public route, skipping auth check')
        setIsLoading(false)
        return
      }

      // Check if already initialized for this protected route and user exists
      if (initializedRef.current && user) {
        console.log('[AuthContext] Already initialized with user, skipping')
        setIsLoading(false)
        return
      }

      // CRITICAL: Load from sessionStorage SYNCHRONOUSLY before setting loading state
      // This prevents race condition where Dashboard checks auth before user is loaded
      const storedUser = typeof window !== 'undefined' ? sessionStorage.getItem('user') : null

      if (storedUser) {
        try {
          const userData = JSON.parse(storedUser)
          console.log('[AuthContext] User loaded from sessionStorage SYNC:', userData.email)

          // Set user and auth state IMMEDIATELY (synchronous)
          setUser(userData)
          setIsAuthenticated(true)
          setIsLoading(false)
          initializedRef.current = true

          // Background refresh (async, doesn't block)
          authService.getCurrentUser().catch(() => {
            console.log('[AuthContext] Background refresh failed, clearing user')
            if (mountedRef.current) {
              setUser(null)
              setIsAuthenticated(false)
            }
          })
          return
        } catch {
          console.log('[AuthContext] Failed to parse stored user, removing')
          sessionStorage.removeItem('user')
        }
      }

      // No cached user - fetch from API
      console.log('[AuthContext] No cached user, starting auth initialization')
      setIsLoading(true)
      initializedRef.current = true

      try {
        console.log('[AuthContext] Fetching user from API')
        const currentUser = await authService.getCurrentUser()

        if (mountedRef.current) {
          console.log('[AuthContext] API returned user:', currentUser?.email || 'null')
          setUser(currentUser)
          setIsAuthenticated(!!currentUser)
          setIsLoading(false)
        }
      } catch (error) {
        console.log('[AuthContext] Auth check failed:', error)
        if (mountedRef.current) {
          setUser(null)
          setIsAuthenticated(false)
          setIsLoading(false)
        }
      }
    }

    initialize()

    return () => {
      mountedRef.current = false
    }
  }, [pathname])

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