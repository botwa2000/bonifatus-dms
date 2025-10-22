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

  // Initialize state from localStorage synchronously
  const getInitialUser = () => {
    if (typeof window === 'undefined') return null
    try {
      const stored = localStorage.getItem('user')
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
    if (initializedRef.current) {
      return
    }
    initializedRef.current = true

    const initialize = async () => {
      const currentPath = pathname || '/'

      if (!isProtectedRoute(currentPath)) {
        setIsLoading(false)
        return
      }

      try {
        const storedUser = typeof window !== 'undefined' ? localStorage.getItem('user') : null

        if (storedUser) {
          try {
            const userData = JSON.parse(storedUser)
            setUser(userData)
            setIsAuthenticated(true)
            setIsLoading(false)

            // Background refresh
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

        // Fetch current user from API
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