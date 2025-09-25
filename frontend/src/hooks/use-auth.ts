// frontend/src/hooks/use-auth.ts
/**
 * Authentication Hook - Production Grade Implementation
 * React hook for managing authentication state and operations
 * Thread-safe, type-safe, with comprehensive error handling
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { authService } from '@/services/auth.service'
import { AuthState, User, AuthError } from '@/types/auth.types'

interface UseAuthReturn {
  authState: AuthState
  login: (code: string, state?: string) => Promise<void>
  logout: () => Promise<void>
  refreshTokens: () => Promise<boolean>
  initializeGoogleAuth: () => Promise<void>
  getCurrentUser: () => Promise<User | null>
  clearError: () => void
}

const initialAuthState: AuthState = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null
}

export function useAuth(): UseAuthReturn {
  const [authState, setAuthState] = useState<AuthState>(initialAuthState)
  const router = useRouter()
  
  // Refs to prevent race conditions in async operations
  const authOperationRef = useRef<Promise<void> | null>(null)
  const mountedRef = useRef(true)

  /**
   * Update authentication state in a type-safe manner
   */
  const updateAuthState = useCallback((updates: Partial<AuthState>) => {
    if (!mountedRef.current) return
    
    setAuthState(prev => ({
      ...prev,
      ...updates
    }))
  }, [])

  /**
   * Handle authentication errors consistently
   */
  const handleAuthError = useCallback((error: any, context: string) => {
    console.error(`Authentication error in ${context}:`, error)
    
    const errorMessage = error?.message || error?.details || 'Authentication failed'
    
    updateAuthState({
      error: errorMessage,
      isLoading: false,
      isAuthenticated: false,
      user: null
    })
    
    return errorMessage
  }, [updateAuthState])

  /**
   * Clear authentication error
   */
  const clearError = useCallback(() => {
    updateAuthState({ error: null })
  }, [updateAuthState])

  /**
   * Login with Google OAuth code
   */
  const login = useCallback(async (code: string, state?: string): Promise<void> => {
    // Prevent concurrent login attempts
    if (authOperationRef.current) {
      await authOperationRef.current
    }

    const loginOperation = async () => {
      try {
        updateAuthState({ 
          isLoading: true, 
          error: null 
        })

        const tokenResponse = await authService.exchangeGoogleToken(code, state)
        
        // Get user profile with the new tokens
        const user = await authService.getCurrentUser()

        updateAuthState({
          user,
          isAuthenticated: true,
          isLoading: false,
          error: null
        })

        console.info(`User ${user.email} authenticated successfully`)

      } catch (error) {
        handleAuthError(error, 'login')
        throw error
      }
    }

    authOperationRef.current = loginOperation()
    await authOperationRef.current
    authOperationRef.current = null
  }, [updateAuthState, handleAuthError])

  /**
   * Logout user and redirect
   */
  const logout = useCallback(async (): Promise<void> => {
    // Prevent concurrent logout attempts
    if (authOperationRef.current) {
      await authOperationRef.current
    }

    const logoutOperation = async () => {
      try {
        updateAuthState({ 
          isLoading: true, 
          error: null 
        })

        await authService.logout()

        updateAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null
        })

        // Redirect to home page
        router.push('/')

      } catch (error) {
        // Even if server logout fails, clear local state
        updateAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null
        })
        
        console.warn('Logout completed with warnings:', error)
        router.push('/')
      }
    }

    authOperationRef.current = logoutOperation()
    await authOperationRef.current
    authOperationRef.current = null
  }, [updateAuthState, router])

  /**
   * Refresh JWT tokens
   */
  const refreshTokens = useCallback(async (): Promise<boolean> => {
    try {
      await authService.refreshToken()
      
      // Get updated user profile
      const user = await authService.getCurrentUser()
      
      updateAuthState({
        user,
        isAuthenticated: true,
        error: null
      })

      return true

    } catch (error) {
      console.warn('Token refresh failed:', error)
      
      // Clear authentication state on refresh failure
      updateAuthState({
        user: null,
        isAuthenticated: false,
        error: null
      })

      return false
    }
  }, [updateAuthState])

  /**
   * Get current user profile
   */
  const getCurrentUser = useCallback(async (): Promise<User | null> => {
    try {
      if (!authService.isAuthenticated()) {
        return null
      }

      const user = await authService.getCurrentUser()
      
      updateAuthState({
        user,
        isAuthenticated: true,
        error: null
      })

      return user

    } catch (error) {
      console.warn('Failed to get current user:', error)
      return null
    }
  }, [updateAuthState])

  /**
   * Initialize Google OAuth flow
   */
  const initializeGoogleAuth = useCallback(async (): Promise<void> => {
    try {
      updateAuthState({ 
        isLoading: true, 
        error: null 
      })

      await authService.initializeGoogleOAuth()

    } catch (error) {
      handleAuthError(error, 'initializeGoogleAuth')
      throw error
    }
  }, [updateAuthState, handleAuthError])

  /**
   * Initialize authentication state on mount
   */
  const initializeAuth = useCallback(async (): Promise<void> => {
    // Prevent concurrent initialization
    if (authOperationRef.current) {
      await authOperationRef.current
      return
    }

    const initOperation = async () => {
      try {
        updateAuthState({ 
          isLoading: true, 
          error: null 
        })

        // Check if user has valid authentication
        if (authService.isAuthenticated()) {
          try {
            const user = await authService.getCurrentUser()
            
            updateAuthState({
              user,
              isAuthenticated: true,
              isLoading: false,
              error: null
            })

          } catch (userError) {
            console.info('Failed to get user, attempting token refresh')
            const refreshSuccess = await refreshTokens()
            
            if (!refreshSuccess) {
              updateAuthState({
                user: null,
                isAuthenticated: false,
                isLoading: false,
                error: null
              })
            }
          }
        } else {
          // No valid authentication found
          updateAuthState({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null
          })
        }

      } catch (initError) {
        console.error('Auth initialization failed:', initError)
        updateAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: 'Authentication initialization failed'
        })
      }
    }

    authOperationRef.current = initOperation()
    await authOperationRef.current
    authOperationRef.current = null
  }, [updateAuthState, refreshTokens])

  /**
   * Handle OAuth callback from URL parameters
   */
  const handleOAuthCallback = useCallback(async (): Promise<void> => {
    if (typeof window === 'undefined') return

    try {
      const urlParams = new URLSearchParams(window.location.search)
      const code = urlParams.get('code')
      const state = urlParams.get('state')
      const error = urlParams.get('error')
      const errorDescription = urlParams.get('error_description')

      // Handle OAuth errors
      if (error) {
        const errorMsg = errorDescription || `OAuth error: ${error}`
        console.error('OAuth callback error:', errorMsg)
        
        updateAuthState({
          error: errorMsg,
          isLoading: false
        })
        
        // Clean up URL
        const cleanUrl = window.location.pathname
        window.history.replaceState({}, document.title, cleanUrl)
        return
      }

      // Handle successful OAuth callback
      if (code) {
        await login(code, state || undefined)
        
        // Clean up URL parameters after successful login
        const cleanUrl = window.location.pathname
        window.history.replaceState({}, document.title, cleanUrl)
      }

    } catch (callbackError) {
      console.error('OAuth callback handling failed:', callbackError)
      handleAuthError(callbackError, 'handleOAuthCallback')
    }
  }, [login, updateAuthState, handleAuthError])

  /**
   * Initialize authentication on component mount
   */
  useEffect(() => {
    mountedRef.current = true

    // Handle OAuth callback first
    handleOAuthCallback().then(() => {
      // Then initialize regular auth state
      return initializeAuth()
    }).catch(error => {
      console.error('Auth initialization failed:', error)
      updateAuthState({
        isLoading: false,
        error: 'Failed to initialize authentication'
      })
    })

    // Cleanup function
    return () => {
      mountedRef.current = false
    }
  }, [handleOAuthCallback, initializeAuth, updateAuthState])

  return {
    authState,
    login,
    logout,
    refreshTokens,
    initializeGoogleAuth,
    getCurrentUser,
    clearError
  }
}