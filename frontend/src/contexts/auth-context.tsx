// frontend/src/contexts/auth-context.tsx
'use client'

import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { authService } from '@/services/auth.service'
import { User } from '@/types/auth.types'

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

  // Load user from API on mount
  // Note: Middleware handles auth redirects, so this only runs on authenticated pages
  useEffect(() => {
    let mounted = true
    let isLoadingUser = false // Prevent race conditions from multiple simultaneous calls

    const loadUser = async () => {
      // Skip loading during OAuth flow to prevent 401 errors
      if (typeof window !== 'undefined' && window.location.pathname === '/login') {
        setIsLoading(false)
        return
      }

      // Prevent multiple simultaneous API calls
      if (isLoadingUser) {
        return
      }

      isLoadingUser = true

      try {
        const currentUser = await authService.getCurrentUser()

        if (mounted) {
          setUser(currentUser)
          setIsAuthenticated(!!currentUser)
          setIsLoading(false)
        }
      } catch (err) {
        // Silently handle errors - expected during OAuth and on public pages
        if (mounted) {
          setUser(null)
          setIsAuthenticated(false)
          setIsLoading(false)
        }
      } finally {
        isLoadingUser = false
      }
    }

    loadUser()

    return () => {
      mounted = false
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
