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
  loadUser: () => Promise<void>
  initializeGoogleAuth: (tierId?: number, billingCycle?: 'monthly' | 'yearly') => Promise<void>
  logout: () => Promise<void>
  clearError: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Passive provider: No auto-fetch on mount
  // Pages that need authentication explicitly call loadUser()
  // This prevents unnecessary API calls and 401 errors on public pages

  const loadUser = useCallback(async () => {
    console.log('[AUTH DEBUG] loadUser called')
    setIsLoading(true)

    try {
      console.log('[AUTH DEBUG] Calling authService.getCurrentUser()')
      const currentUser = await authService.getCurrentUser()
      console.log('[AUTH DEBUG] getCurrentUser response:', currentUser ? `User: ${currentUser.email}` : 'null')
      setUser(currentUser)
      setIsAuthenticated(!!currentUser)
      console.log('[AUTH DEBUG] Auth state updated - isAuthenticated:', !!currentUser)
    } catch (err) {
      console.error('[AUTH DEBUG] Error in loadUser:', err)
      // Silently handle errors
      setUser(null)
      setIsAuthenticated(false)
      console.log('[AUTH DEBUG] Auth state cleared due to error')
    } finally {
      setIsLoading(false)
      console.log('[AUTH DEBUG] loadUser completed')
    }
  }, [])

  const initializeGoogleAuth = useCallback(async (tierId?: number, billingCycle?: 'monthly' | 'yearly') => {
    try {
      setIsLoading(true)
      setError(null)
      await authService.initializeGoogleOAuth(tierId, billingCycle)
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

      // Clear theme preference and reset to light mode for logged-out users
      if (typeof window !== 'undefined') {
        localStorage.removeItem('theme')
        document.documentElement.classList.remove('dark')
        document.documentElement.classList.add('light')
      }

      window.location.href = '/'
    } catch (err) {
      console.error('[AuthProvider] Logout failed:', err)
      setUser(null)
      setIsAuthenticated(false)

      // Clear theme even on logout failure
      if (typeof window !== 'undefined') {
        localStorage.removeItem('theme')
        document.documentElement.classList.remove('dark')
        document.documentElement.classList.add('light')
      }

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
      loadUser,
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
