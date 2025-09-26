// frontend/src/hooks/use-auth.ts

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { authService } from '@/services/auth.service'
import { AuthState, User } from '@/types/auth.types'

interface UseAuthReturn {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (code: string, state?: string) => Promise<void>
  logout: () => Promise<void>
  refreshTokens: () => Promise<boolean>
  initializeGoogleAuth: () => Promise<void>
  getCurrentUser: () => Promise<User | null>
  handleGoogleCallback: () => Promise<void>
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
  
  const authOperationRef = useRef<Promise<void> | null>(null)
  const mountedRef = useRef(true)

  const updateAuthState = useCallback((updates: Partial<AuthState>) => {
    if (!mountedRef.current) return
    
    setAuthState(prev => ({
      ...prev,
      ...updates
    }))
  }, [])

  const handleAuthError = useCallback((error: unknown, context: string) => {
    console.error(`Authentication error in ${context}:`, error)
    
    let errorMessage = 'Authentication failed'
    
    if (error instanceof Error) {
      errorMessage = error.message
    } else if (typeof error === 'object' && error !== null) {
      const errorObj = error as Record<string, unknown>
      errorMessage = (errorObj.message || errorObj.details || errorMessage) as string
    }
    
    updateAuthState({
      error: errorMessage,
      isLoading: false,
      isAuthenticated: false,
      user: null
    })
    
    return errorMessage
  }, [updateAuthState])

  const clearError = useCallback(() => {
    updateAuthState({ error: null })
  }, [updateAuthState])

  const login = useCallback(async (code: string, state?: string) => {
    if (authOperationRef.current) {
      return authOperationRef.current
    }

    const operation = async () => {
      try {
        updateAuthState({ 
          isLoading: true, 
          error: null 
        })

        const response = await authService.exchangeGoogleToken(code, state)
        
        updateAuthState({
          user: response.user,
          isAuthenticated: true,
          isLoading: false,
          error: null
        })

        router.push('/dashboard')

      } catch (error) {
        handleAuthError(error, 'login')
      } finally {
        authOperationRef.current = null
      }
    }

    authOperationRef.current = operation()
    return authOperationRef.current
  }, [updateAuthState, handleAuthError, router])

  const logout = useCallback(async () => {
    if (authOperationRef.current) {
      return authOperationRef.current
    }

    const operation = async () => {
      try {
        updateAuthState({ isLoading: true })

        await authService.logout()
        
        updateAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null
        })

        router.push('/')

      } catch (error) {
        handleAuthError(error, 'logout')
      } finally {
        authOperationRef.current = null
      }
    }

    authOperationRef.current = operation()
    return authOperationRef.current
  }, [updateAuthState, handleAuthError, router])

  const refreshTokens = useCallback(async (): Promise<boolean> => {
    try {
      const success = await authService.refreshTokens()
      
      if (!success) {
        updateAuthState({
          user: null,
          isAuthenticated: false,
          error: 'Session expired'
        })
      }
      
      return success

    } catch (error) {
      handleAuthError(error, 'refreshTokens')
      return false
    }
  }, [updateAuthState, handleAuthError])

  const initializeGoogleAuth = useCallback(async () => {
    try {
      updateAuthState({ 
        isLoading: true, 
        error: null 
      })

      await authService.initializeGoogleOAuth()

    } catch (error) {
      handleAuthError(error, 'initializeGoogleAuth')
    }
  }, [updateAuthState, handleAuthError])

  const getCurrentUser = useCallback(async (): Promise<User | null> => {
    try {
      const user = await authService.getCurrentUser()
      
      if (user) {
        updateAuthState({
          user,
          isAuthenticated: true,
          isLoading: false
        })
      } else {
        updateAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false
        })
      }
      
      return user

    } catch (error) {
      handleAuthError(error, 'getCurrentUser')
      return null
    }
  }, [updateAuthState, handleAuthError])

  const initializeAuth = useCallback(async () => {
    try {
      updateAuthState({ isLoading: true })

      const user = await authService.getCurrentUser()
      
      updateAuthState({
        user,
        isAuthenticated: !!user,
        isLoading: false,
        error: null
      })

    } catch (error) {
      console.error('Auth initialization failed:', error)
      updateAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null
      })
    }
  }, [updateAuthState])

  const handleGoogleCallback = useCallback(async () => {
    try {
      const urlParams = new URLSearchParams(window.location.search)
      const code = urlParams.get('code')
      const state = urlParams.get('state')
      const error = urlParams.get('error')
      const errorDescription = urlParams.get('error_description')

      if (error) {
        const errorMsg = errorDescription || `OAuth error: ${error}`
        console.error('OAuth callback error:', errorMsg)
        
        updateAuthState({
          error: errorMsg,
          isLoading: false
        })
        
        const cleanUrl = window.location.pathname
        window.history.replaceState({}, document.title, cleanUrl)
        return
      }

      if (code) {
        await login(code, state || undefined)
        
        const cleanUrl = window.location.pathname
        window.history.replaceState({}, document.title, cleanUrl)
      }

    } catch (callbackError) {
      console.error('OAuth callback handling failed:', callbackError)
      handleAuthError(callbackError, 'handleGoogleCallback')
    }
  }, [login, updateAuthState, handleAuthError])

  useEffect(() => {
    mountedRef.current = true

    const urlParams = new URLSearchParams(window.location.search)
    const hasOAuthParams = urlParams.get('code') || urlParams.get('error')

    if (hasOAuthParams) {
      handleGoogleCallback().then(() => {
        return initializeAuth()
      }).catch(error => {
        console.error('Auth initialization failed:', error)
        updateAuthState({
          isLoading: false,
          error: 'Failed to initialize authentication'
        })
      })
    } else {
      initializeAuth()
    }

    return () => {
      mountedRef.current = false
    }
  }, [handleGoogleCallback, initializeAuth, updateAuthState])

  return {
    user: authState.user,
    isAuthenticated: authState.isAuthenticated,
    isLoading: authState.isLoading,
    error: authState.error,
    login,
    logout,
    refreshTokens,
    initializeGoogleAuth,
    getCurrentUser,
    handleGoogleCallback,
    clearError
  }
}