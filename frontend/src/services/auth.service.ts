// frontend/src/services/auth.service.ts

import { apiClient } from './api-client'
import { TokenResponse, User, GoogleOAuthConfig, AuthError } from '@/types/auth.types'

interface AuthServiceConfig {
  apiUrl: string
  tokenRefreshThreshold: number
  maxRetries: number
}

interface JWTPayload {
  exp: number
  iat: number
  sub: string
  email?: string
  [key: string]: unknown
}

export class AuthService {
  private readonly config: AuthServiceConfig
  private tokenRefreshPromise: Promise<boolean> | null = null
  private refreshTimeoutId: NodeJS.Timeout | null = null
  private oauthConfigCache: GoogleOAuthConfig | null = null

  constructor() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL

    if (!apiUrl) {
      throw new Error('NEXT_PUBLIC_API_URL environment variable is required')
    }

    this.config = {
      apiUrl,
      tokenRefreshThreshold: 5 * 60 * 1000,
      maxRetries: 3
    }

    if (typeof window !== 'undefined') {
      this.initializeTokenRefresh()
    }
  }

  private checkSessionStorageAvailable(): boolean {
    try {
      const testKey = '__test__'
      sessionStorage.setItem(testKey, 'test')
      sessionStorage.removeItem(testKey)
      return true
    } catch (e) {
      console.error('SessionStorage not available:', e)
      return false
    }
  }


  private isClientSide(): boolean {
    return typeof window !== 'undefined'
  }

  async getOAuthConfig(): Promise<GoogleOAuthConfig> {
    if (this.oauthConfigCache) {
      return this.oauthConfigCache
    }

    try {
      const response = await apiClient.get<{ google_client_id: string; redirect_uri: string }>('/api/v1/auth/google/config')

      this.oauthConfigCache = {
        google_client_id: response.google_client_id,
        redirect_uri: response.redirect_uri,
        scope: 'openid email profile'
      }

      return this.oauthConfigCache
    } catch (error) {
      console.error('Failed to fetch OAuth config:', error)
      throw new Error('Unable to initialize authentication')
    }
  }

  generateSecureState(): string {
    const array = new Uint8Array(32)
    crypto.getRandomValues(array)
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('')
  }

  storeOAuthState(state: string): void {
    console.log('[AUTH DEBUG] Attempting to store state:', state.substring(0, 20) + '...')
    
    if (!this.checkSessionStorageAvailable()) {
      throw new Error('SessionStorage is not available. Please check browser privacy settings.')
    }
    
    try {
      sessionStorage.setItem('oauth_state', state)
      sessionStorage.setItem('oauth_state_timestamp', Date.now().toString())
      
      // Verify it was stored
      const stored = sessionStorage.getItem('oauth_state')
      console.log('[AUTH DEBUG] State stored successfully:', stored === state)
      console.log('[AUTH DEBUG] Stored value:', stored?.substring(0, 20) + '...')
    } catch (error) {
      console.error('[AUTH DEBUG] Failed to store state:', error)
      throw new Error('Failed to store OAuth state: ' + (error as Error).message)
    }
  }

  validateOAuthState(receivedState: string): boolean {
    const storedState = sessionStorage.getItem('oauth_state')
    const timestamp = sessionStorage.getItem('oauth_state_timestamp')
    
    if (!storedState || !timestamp) {
      return false
    }

    const age = Date.now() - parseInt(timestamp)
    const maxAge = 10 * 60 * 1000 // 10 minutes

    if (age > maxAge) {
      this.clearStoredOAuthState()
      return false
    }

    return storedState === receivedState
  }

  clearStoredOAuthState(): void {
    sessionStorage.removeItem('oauth_state')
    sessionStorage.removeItem('oauth_state_timestamp')
  }

  async initializeGoogleOAuth(): Promise<void> {
    console.log('[AUTH DEBUG] Starting OAuth initialization')
    
    try {
      const config = await this.getOAuthConfig()
      console.log('[AUTH DEBUG] Got OAuth config:', config.redirect_uri)
      
      const state = this.generateSecureState()
      console.log('[AUTH DEBUG] Generated state:', state.substring(0, 20) + '...')
      
      const params = new URLSearchParams({
        client_id: config.google_client_id,
        redirect_uri: config.redirect_uri,
        response_type: 'code',
        scope: config.scope,
        access_type: 'offline',
        prompt: 'consent',
        state
      })

      const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`
      console.log('[AUTH DEBUG] Generated auth URL with state')
      
      this.storeOAuthState(state)
      console.log('[AUTH DEBUG] About to redirect to Google')
      
      window.location.href = authUrl
      
    } catch (error) {
      console.error('[AUTH DEBUG] OAuth initialization failed:', error)
      throw new Error('Authentication service unavailable: ' + (error as Error).message)
    }
  }
  
  async exchangeGoogleToken(
    code: string,
    state: string | null
  ): Promise<{ success: boolean; error?: string }> {
    try {
      console.log('[AUTH DEBUG] Starting token exchange')

      // Validate state if provided
      if (state && !this.validateOAuthState(state)) {
        throw new Error('Invalid OAuth state - possible security issue')
      }

      // Exchange authorization code for JWT tokens via backend
      // Backend will set httpOnly cookies automatically
      await apiClient.post<TokenResponse>('/api/v1/auth/google/callback', {
        code,
        state: state || ''
      })

      console.log('[AUTH DEBUG] Token exchange successful')

      // Backend sets secure httpOnly cookies (access_token, refresh_token)
      // These are automatically sent with subsequent API requests

      // Clear OAuth state
      this.clearStoredOAuthState()

      return { success: true }

    } catch (error) {
      console.error('Token exchange failed:', error)
      this.clearStoredOAuthState()

      const errorMessage = error instanceof Error ? error.message : 'Authentication failed'
      return { success: false, error: errorMessage }
    }
  }

  // Tokens are stored in secure httpOnly cookies by backend
  // Frontend cannot and should not access them directly
  // This is a security feature, not a limitation

  isTokenExpired(token: string): boolean {
    try {
      const payload = this.decodeJWTPayload(token)
      return Date.now() >= payload.exp * 1000 - this.config.tokenRefreshThreshold
    } catch {
      return true
    }
  }

  decodeJWTPayload(token: string): JWTPayload {
    const parts = token.split('.')
    if (parts.length !== 3) {
      throw new Error('Invalid JWT format')
    }
    
    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded)
  }

  async getCurrentUser(): Promise<User | null> {
    try {
      // httpOnly cookies are sent automatically with this request
      const response = await apiClient.get<User>('/api/v1/auth/me', true)

      // Cache user info in localStorage for UI display (non-sensitive data only)
      if (typeof window !== 'undefined') {
        localStorage.setItem('user', JSON.stringify(response))
      }

      return response

    } catch (error) {
        // Silent fail for 401 on public pages (expected behavior)
        const apiError = error as { status?: number; message?: string }
        if (apiError?.status !== 401) {
            console.error('Failed to get current user:', error)
        }

        // Clear stale data on auth failure
        if (apiError?.status === 401) {
          this.clearAllAuthData()
        }

        return null
    }
  }

  async refreshTokens(): Promise<boolean> {
    if (this.tokenRefreshPromise) {
      try {
        return await this.tokenRefreshPromise
      } catch {
        return false
      }
    }

    try {
      // Create the promise that returns boolean
      this.tokenRefreshPromise = (async () => {
        try {
          // Refresh token is in httpOnly cookie, sent automatically
          await apiClient.post<{ access_token: string; expires_in: number }>(
            '/api/v1/auth/refresh', 
            {},
            true
          )
          return true
        } catch {
          this.clearAllAuthData()
          return false
        }
      })()
      
      return await this.tokenRefreshPromise

    } catch (error) {
      console.error('Token refresh failed:', error)
      this.clearAllAuthData()
      return false
    } finally {
      this.tokenRefreshPromise = null
    }
  }

  scheduleTokenRefresh(): void {
      // Token refresh is now handled by API client on 401 responses
      // This method kept for backward compatibility but does nothing
  }

  clearTokenRefresh(): void {
    if (this.refreshTimeoutId) {
      clearTimeout(this.refreshTimeoutId)
      this.refreshTimeoutId = null
    }
  }

  initializeTokenRefresh(): void {
    // Token refresh is now handled automatically by backend via cookies
    // This method kept for backward compatibility but does nothing
  }

  async logout(): Promise<void> {
    try {
      await apiClient.delete('/api/v1/auth/logout', true)
    } catch (error) {
      console.error('Logout request failed:', error)
    } finally {
      this.clearTokenRefresh()
      this.clearAllAuthData()
    }
  }

  clearAllAuthData(): void {
    // Clear cached user data from localStorage
    if (typeof window !== 'undefined') {
      localStorage.removeItem('user')
    }

    // httpOnly cookies are cleared by backend /logout endpoint
    // Frontend cannot access or clear httpOnly cookies (by design for security)
  }

  handleAuthError(error: unknown): AuthError {
    let authError: AuthError

    if (error instanceof Error) {
      authError = error as AuthError
    } else if (typeof error === 'object' && error !== null) {
      const errorObj = error as Record<string, unknown>
      authError = new Error(errorObj.message as string || 'Authentication failed') as AuthError
      authError.status = errorObj.status as number
      authError.code = errorObj.code as string
    } else {
      authError = new Error('Unknown authentication error') as AuthError
    }

    if (authError.status === 401 || authError.status === 403) {
      this.clearAllAuthData()
    }

    return authError
  }

  async getTrialInfo(): Promise<{ days_remaining: number; expires_at: string; features: string[] } | null> {
    try {
      const user = await this.getCurrentUser()
      if (!user) return null

      // For now, return placeholder trial info
      // This should be implemented when trial system is added
      return {
        days_remaining: 30,
        expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        features: ['premium_storage', 'ai_categorization', 'priority_support']
      }
    } catch (error) {
      console.error('Failed to get trial info:', error)
      return null
    }
  }

  isTrialActive(): boolean {
    // Placeholder implementation
    // This should check actual trial status when trial system is implemented
    return true
  }

}

export const authService = new AuthService()