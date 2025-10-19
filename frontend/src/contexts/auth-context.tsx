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

// Global singleton to prevent multiple auth initializations across page prefetches
let globalAuthInitialized = false
let globalInitPromise: Promise<User | null> | null = null

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  // Only show loading state for protected routes
  const [user, setUser] = useState<User | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(isProtectedRoute(pathname || '/'))
  const [error, setError] = useState<string | null>(null)
  const initPromiseRef = useRef<Promise<void> | null>(null)
  const initializedRef = useRef(false)
  const mountedRef = useRef(true)

  // Initialize auth ONCE globally (survives prefetch renders)
  useEffect(() => {
    if (initializedRef.current || globalAuthInitialized) {
      return
    }

    mountedRef.current = true
    initializedRef.current = true
    globalAuthInitialized = true

    const initialize = async () => {
      const currentPath = pathname || '/'

      if (!isProtectedRoute(currentPath)) {
        if (mountedRef.current) {
          setIsLoading(false)
        }
        return
      }

      if (globalInitPromise) {
        try {
          const cachedUser = await globalInitPromise
          if (mountedRef.current) {
            setUser(cachedUser)
            setIsAuthenticated(!!cachedUser)
            setIsLoading(false)
          }
        } catch {
          if (mountedRef.current) {
            setIsLoading(false)
          }
        }
        return
      }

      globalInitPromise = (async () => {
        try {
          const storedUser = typeof window !== 'undefined' ? localStorage.getItem('user') : null

          if (storedUser) {
            try {
              const userData = JSON.parse(storedUser)
              if (mountedRef.current) {
                setUser(userData)
                setIsAuthenticated(true)
                setIsLoading(false)
              }

              authService.getCurrentUser().catch(() => {
                if (mountedRef.current) {
                  setUser(null)
                  setIsAuthenticated(false)
                }
              })

              return userData
            } catch {
              localStorage.removeItem('user')
            }
          }

          const currentUser = await authService.getCurrentUser()

          if (mountedRef.current) {
            setUser(currentUser)
            setIsAuthenticated(!!currentUser)
            setIsLoading(false)
          }

          return currentUser
        } catch {
          if (mountedRef.current) {
            setUser(null)
            setIsAuthenticated(false)
            setIsLoading(false)
          }
          return null
        }
      })()

      await globalInitPromise
    }

    initialize()

    return () => {
      mountedRef.current = false
    }
  }, [])

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