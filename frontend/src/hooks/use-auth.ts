// frontend/src/hooks/use-auth.ts
'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { authService } from '@/services/auth.service'
import { User } from '@/types/auth.types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

export function useAuth() {
  const router = useRouter()
  const mountedRef = useRef(true)
  const authOperationRef = useRef<Promise<void> | null>(null)
  const processedCodesRef = useRef<Set<string>>(new Set())
  
  // Ref for auth initialization promise to prevent parallel calls
  const authInitPromiseRef = useRef<Promise<void> | null>(null)
  
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    error: null
  })

  const updateAuthState = useCallback((updates: Partial<AuthState>) => {
    if (!mountedRef.current) return
    
    setAuthState(prev => ({
      ...prev,
      ...updates
    }))
  }, [])

  const clearError = useCallback(() => {
    updateAuthState({ error: null })
  }, [updateAuthState])

  const handleAuthError = useCallback((error: unknown, context: string) => {
    if (!mountedRef.current) return

    console.error(`Auth error in ${context}:`, error)
    
    const errorMessage = error instanceof Error 
      ? error.message 
      : 'An authentication error occurred'

    updateAuthState({
      error: errorMessage,
      isLoading: false
    })
  }, [updateAuthState])

  const login = useCallback(async (code: string, state?: string) => {
    if (authOperationRef.current) {
      return authOperationRef.current
    }

    if (processedCodesRef.current.has(code)) {
      console.warn('Code already processed, skipping duplicate login')
      return
    }

    const operation = async () => {
      try {
        processedCodesRef.current.add(code)
        
        updateAuthState({ 
          isLoading: true, 
          error: null 
        })

        const response = await authService.exchangeGoogleToken(
          code, 
          state || null
        )
        
        if (response.success) {
          const user = await authService.getCurrentUser()
          
          updateAuthState({
            user: user,
            isAuthenticated: true,
            isLoading: false,
            error: null
          })

          router.push('/dashboard')
        } else {
          processedCodesRef.current.delete(code)
          throw new Error(response.error || 'Authentication failed')
        }

      } catch (error) {
        processedCodesRef.current.delete(code)
        handleAuthError(error, 'login')
      } finally {
        authOperationRef.current = null
      }
    }

    authOperationRef.current = operation()
    await authOperationRef.current
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

        window.location.href = '/'

      } catch (error) {
        console.error('Logout error:', error)
        updateAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null
        })
        window.location.href = '/'
      } finally {
        authOperationRef.current = null
      }
    }

    authOperationRef.current = operation()
    return authOperationRef.current
  }, [updateAuthState])

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
    // Return existing promise if initialization already in progress
    if (authInitPromiseRef.current) {
      console.debug('[Auth] Initialization already in progress, waiting...')
      return authInitPromiseRef.current
    }

    authInitPromiseRef.current = (async () => {
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
      } finally {
        // Clear promise after completion
        authInitPromiseRef.current = null
      }
    })()

    return authInitPromiseRef.current
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