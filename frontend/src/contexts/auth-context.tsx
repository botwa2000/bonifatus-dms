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

  // Initialize auth ONCE on mount
  useEffect(() => {
    if (initializedRef.current) {
      return
    }

    mountedRef.current = true
    initializedRef.current = true

    const initialize = async () => {
      const currentPath = pathname || '/'

      if (!isProtectedRoute(currentPath)) {
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

              return
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
        } catch {
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
  }, []) // Empty deps - run ONCE on mount only

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