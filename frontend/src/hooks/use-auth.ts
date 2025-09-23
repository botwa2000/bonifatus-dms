// src/hooks/use-auth.ts
/**
 * Authentication hook for managing user authentication state
 * Handles login, logout, token refresh, and Google OAuth callback
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { authService } from '@/services/auth.service'
import { AuthState, User } from '@/types/auth.types'

interface UseAuthReturn extends AuthState {
  login: (googleToken: string) => Promise<void>
  logout: () => Promise<void>
  refreshTokens: () => Promise<boolean>
  initializeAuth: () => Promise<void>
  handleGoogleCallback: () => Promise<void>
  redirectToGoogleAuth: () => Promise<void>
}

export function useAuth(): UseAuthReturn {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true
  })

  // Ref to prevent multiple simultaneous auth operations
  const authOperationRef = useRef<Promise<void> | null>(null)
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  /**
   * Clear token refresh schedule
   */
  const clearTokenRefreshSchedule = useCallback(() => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current)
      refreshTimeoutRef.current = null
    }
  }, [])

  /**
   * Schedule automatic token refresh
   */
  const scheduleTokenRefresh = useCallback(() => {
    clearTokenRefreshSchedule()
    
    refreshTimeoutRef.current = setTimeout(async () => {
      try {
        const storedTokens = authService.getStoredTokens()
        if (storedTokens) {
          await authService.refreshToken(storedTokens.refresh_token)
          const user = await authService.getCurrentUser()
          setAuthState({
            user,
            isAuthenticated: true,
            isLoading: false
          })
          scheduleTokenRefresh() // Reschedule next refresh
        }
      } catch {
        setAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false
        })
      }
    }, 45 * 60 * 1000) // 45 minutes
  }, [clearTokenRefreshSchedule])

  /**
   * Update authentication state
   */
  const updateAuthState = useCallback((user: User | null): void => {
    setAuthState({
      user,
      isAuthenticated: !!user,
      isLoading: false
    })

    clearTokenRefreshSchedule()
    
    if (user) {
      scheduleTokenRefresh()
    }
  }, [clearTokenRefreshSchedule, scheduleTokenRefresh])

  /**
   * Refresh authentication tokens
   */
  const refreshTokens = useCallback(async (): Promise<boolean> => {
    try {
      const storedTokens = authService.getStoredTokens()
      if (!storedTokens) {
        updateAuthState(null)
        return false
      }

      await authService.refreshToken(storedTokens.refresh_token)
      
      const user = await authService.getCurrentUser()
      updateAuthState(user)
      
      return true
    } catch (refreshError) {
      console.error('Token refresh failed:', refreshError)
      updateAuthState(null)
      return false
    }
  }, [updateAuthState])

  /**
   * Login with Google OAuth token
   */
  const login = useCallback(async (googleToken: string): Promise<void> => {
    // Prevent multiple simultaneous login attempts
    if (authOperationRef.current) {
      await authOperationRef.current
      return
    }

    const loginOperation = async () => {
      try {
        setAuthState(prev => ({ ...prev, isLoading: true }))
        
        await authService.exchangeGoogleToken(googleToken)
        
        const user = await authService.getCurrentUser()
        updateAuthState(user)
        
      } catch (loginError) {
        console.error('Login failed:', loginError)
        updateAuthState(null)
        throw loginError
      }
    }

    authOperationRef.current = loginOperation()
    await authOperationRef.current
    authOperationRef.current = null
  }, [updateAuthState])

  /**
   * Logout user
   */
  const logout = useCallback(async (): Promise<void> => {
    // Prevent multiple simultaneous logout attempts
    if (authOperationRef.current) {
      await authOperationRef.current
      return
    }

    const logoutOperation = async () => {
      try {
        setAuthState(prev => ({ ...prev, isLoading: true }))
        await authService.logout()
      } catch (logoutError) {
        console.error('Logout error:', logoutError)
      } finally {
        updateAuthState(null)
      }
    }

    authOperationRef.current = logoutOperation()
    await authOperationRef.current
    authOperationRef.current = null
  }, [updateAuthState])

  /**
   * Initialize authentication state from stored tokens
   */
  const initializeAuth = useCallback(async (): Promise<void> => {
    // Prevent multiple simultaneous initialization
    if (authOperationRef.current) {
      await authOperationRef.current
      return
    }

    const initOperation = async () => {
      try {
        const storedTokens = authService.getStoredTokens()
        if (!storedTokens) {
          updateAuthState(null)
          return
        }

        // Validate token format
        if (!authService.validateTokenFormat(storedTokens)) {
          console.warn('Invalid token format, clearing tokens')
          authService.clearTokens()
          updateAuthState(null)
          return
        }

        // Check if tokens are likely expired
        if (authService.areTokensLikelyExpired()) {
          console.info('Tokens likely expired, attempting refresh')
          const refreshSuccess = await refreshTokens()
          if (!refreshSuccess) {
            updateAuthState(null)
          }
          return
        }

        // Try to get user with existing tokens
        try {
          const user = await authService.getCurrentUser()
          updateAuthState(user)
        } catch {
          console.info('Failed to get user, attempting token refresh')
          const refreshSuccess = await refreshTokens()
          if (!refreshSuccess) {
            updateAuthState(null)
          }
        }
        
      } catch (initError) {
        console.error('Auth initialization failed:', initError)
        updateAuthState(null)
      }
    }

    authOperationRef.current = initOperation()
    await authOperationRef.current
    authOperationRef.current = null
  }, [refreshTokens, updateAuthState])

  /**
   * Handle Google OAuth callback from URL parameters
   */
  const handleGoogleCallback = useCallback(async (): Promise<void> => {
    if (typeof window === 'undefined') return

    try {
      const urlParams = new URLSearchParams(window.location.search)
      const code = urlParams.get('code')
      const error = urlParams.get('error')

      if (error) {
        console.error('OAuth callback error:', error)
        const errorDescription = urlParams.get('error_description') || 'Unknown OAuth error'
        updateAuthState(null)
        throw new Error(`Authentication failed: ${errorDescription}`)
      }

      if (code) {
        await login(code)
        
        // Clean up URL parameters after successful login
        const cleanUrl = window.location.pathname
        window.history.replaceState({}, document.title, cleanUrl)
      }
    } catch (callbackError) {
      console.error('Google callback handling failed:', callbackError)
      updateAuthState(null)
      throw callbackError
    }
  }, [login, updateAuthState])

  /**
   * Redirect to Google OAuth authorization
   */
  const redirectToGoogleAuth = useCallback(async (): Promise<void> => {
    try {
      const authUrl = await authService.initializeGoogleOAuth()
      window.location.href = authUrl
    } catch (redirectError) {
      console.error('Google auth redirect failed:', redirectError)
      throw new Error('Failed to initialize authentication')
    }
  }, [])

  /**
   * Initialize authentication on mount
   */
  useEffect(() => {
    initializeAuth()
    
    // Cleanup on unmount
    return () => {
      clearTokenRefreshSchedule()
      authOperationRef.current = null
    }
  }, [initializeAuth, clearTokenRefreshSchedule])

  /**
   * Handle OAuth callback if present in URL
   */
  useEffect(() => {
    if (typeof window === 'undefined') return
    
    const urlParams = new URLSearchParams(window.location.search)
    const hasOAuthParams = urlParams.has('code') || urlParams.has('error')
    
    if (hasOAuthParams) {
      handleGoogleCallback().catch(error => {
        console.error('OAuth callback failed:', error)
      })
    }
  }, [handleGoogleCallback])

  /**
   * Handle browser tab visibility changes to refresh tokens
   */
  useEffect(() => {
    if (typeof window === 'undefined') return

    const handleVisibilityChange = () => {
      if (!document.hidden && authState.isAuthenticated) {
        // Check if tokens need refresh when tab becomes visible
        if (authService.areTokensLikelyExpired()) {
          refreshTokens()
        }
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [authState.isAuthenticated, refreshTokens])

  return {
    ...authState,
    login,
    logout,
    refreshTokens,
    initializeAuth,
    handleGoogleCallback,
    redirectToGoogleAuth
  }
}