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
  const [user, setUser] = useState<User | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const initPromiseRef = useRef<Promise<void> | null>(null)
  const initializedRef = useRef(false)
  const mountedRef = useRef(true)
  const pathname = usePathname()

  // Initialize auth ONCE on mount (skip for public routes)
  useEffect(() => {
    // Only initialize once per session
    if (initializedRef.current) {
      return
    }

    mountedRef.current = true
    initializedRef.current = true

    const initialize = async () => {
      // Skip auth check on public routes to avoid unnecessary API calls
      if (!isProtectedRoute(pathname || '/')) {
        if (mountedRef.current) {
          setIsLoading(false)
        }
        return
      }

      if (initPromiseRef.current) {
        return initPromiseRef.current
      }

      initPromiseRef.current = (async () => {
        try {
          // Check localStorage first to avoid race condition after login redirect
          const storedUser = typeof window !== 'undefined' ? localStorage.getItem('user') : null

          if (storedUser) {
            try {
              const userData = JSON.parse(storedUser)
              if (mountedRef.current) {
                setUser(userData)
                setIsAuthenticated(true)
                setIsLoading(false)
              }

              // Verify with API in background (don't block UI)
              authService.getCurrentUser().catch(() => {
                // If API call fails, clear state
                if (mountedRef.current) {
                  setUser(null)
                  setIsAuthenticated(false)
                }
              })

              return
            } catch (e) {
              // Invalid localStorage data, fall through to API call
              localStorage.removeItem('user')
            }
          }

          // No cached user, fetch from API
          const currentUser = await authService.getCurrentUser()

          if (mountedRef.current) {
            setUser(currentUser)
            setIsAuthenticated(!!currentUser)
            setIsLoading(false)
          }
        } catch (err) {
          // Silently handle 401 errors (expected when not logged in)
          if (mountedRef.current) {
            setUser(null)
            setIsAuthenticated(false)
            setIsLoading(false)
          }
        }
      })()

      return initPromiseRef.current
    }

    initialize()

    return () => {
      mountedRef.current = false
    }
  }, [pathname]) // pathname dependency needed for initial route detection

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