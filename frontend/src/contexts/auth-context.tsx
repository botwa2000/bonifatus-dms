// frontend/src/contexts/auth-context.tsx
'use client'

import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { authService } from '@/services/auth.service'
import { User } from '@/types/auth.types'
import { identifyUser, trackLogout, resetUser } from '@/lib/analytics'
import { logger } from '@/lib/logger'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  hasAttemptedAuth: boolean
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
  const [isLoading, setIsLoading] = useState(false)  // Start false for public pages
  const [hasAttemptedAuth, setHasAttemptedAuth] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Passive provider: No auto-fetch on mount
  // Pages that need authentication explicitly call loadUser()
  // loadUser() sets isLoading=true at start to prevent race conditions
  // This prevents unnecessary API calls and 401 errors on public pages

  const loadUser = useCallback(async () => {
    logger.debug('[AUTH DEBUG] loadUser called')
    setIsLoading(true)

    try {
      logger.debug('[AUTH DEBUG] Calling authService.getCurrentUser()')
      const currentUser = await authService.getCurrentUser()
      logger.debug('[AUTH DEBUG] getCurrentUser response:', currentUser ? `User: ${currentUser.email}` : 'null')
      setUser(currentUser)
      setIsAuthenticated(!!currentUser)
      logger.debug('[AUTH DEBUG] Auth state updated - isAuthenticated:', !!currentUser)

      // Identify user for analytics
      if (currentUser) {
        identifyUser(currentUser.id, {
          email: currentUser.email,
          full_name: currentUser.full_name,
          tier: currentUser.tier,
          created_at: currentUser.created_at,
        })
      }
    } catch (err) {
      logger.error('[AUTH DEBUG] Error in loadUser:', err)
      // Silently handle errors
      setUser(null)
      setIsAuthenticated(false)
      logger.debug('[AUTH DEBUG] Auth state cleared due to error')
    } finally {
      setIsLoading(false)
      setHasAttemptedAuth(true)
      logger.debug('[AUTH DEBUG] loadUser completed')
    }
  }, [])

  const initializeGoogleAuth = useCallback(async (tierId?: number, billingCycle?: 'monthly' | 'yearly') => {
    try {
      setIsLoading(true)
      setError(null)
      await authService.initializeGoogleOAuth(tierId, billingCycle)
    } catch (err) {
      logger.error('[AuthProvider] Google auth failed:', err)
      setError(err instanceof Error ? err.message : 'Authentication failed')
      setIsLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      // Track logout event
      trackLogout()
      resetUser()

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
      logger.error('[AuthProvider] Logout failed:', err)
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
      hasAttemptedAuth,
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
