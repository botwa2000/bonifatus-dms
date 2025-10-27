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
    let isLoading = false // Prevent race conditions from multiple simultaneous calls
    const isDevelopment = process.env.NODE_ENV === 'development'

    const loadUser = async () => {
      // Prevent multiple simultaneous API calls
      if (isLoading) {
        if (isDevelopment) {
          console.log('[AuthContext] ⏩ Skipping duplicate user load request')
        }
        return
      }

      isLoading = true
      const requestId = Math.random().toString(36).substr(2, 9)

      try {
        if (isDevelopment) {
          console.log(`[AuthContext:${requestId}] 🔄 Loading user from API...`)
          console.log(`[AuthContext:${requestId}] 🍪 Document cookies:`, document.cookie.split('; ').filter(c => c.includes('token')))
        }

        const currentUser = await authService.getCurrentUser()

        if (mounted) {
          if (isDevelopment) {
            console.log(`[AuthContext:${requestId}] ✅ User loaded:`, currentUser?.email || 'null')
          }
          setUser(currentUser)
          setIsAuthenticated(!!currentUser)
          setIsLoading(false)
        }
      } catch (err) {
        if (isDevelopment) {
          const errorMsg = err instanceof Error ? err.message : 'Unknown error'
          console.log(`[AuthContext:${requestId}] ❌ Failed to load user:`, errorMsg)
        }
        if (mounted) {
          setUser(null)
          setIsAuthenticated(false)
          setIsLoading(false)
        }
      } finally {
        isLoading = false
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
