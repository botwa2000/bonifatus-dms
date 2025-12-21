// frontend/src/services/auth.service.ts

import { apiClient } from './api-client'
import { User, GoogleOAuthConfig, AuthError } from '@/types/auth.types'
import { logger } from '@/lib/logger'
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
      logger.error('SessionStorage not available:', e)
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
      logger.error('Failed to fetch OAuth config:', error)
      throw new Error('Unable to initialize authentication')
    }
  }

  generateSecureState(tierId?: number, billingCycle?: 'monthly' | 'yearly'): string {
    const array = new Uint8Array(32)
    crypto.getRandomValues(array)
    const csrfToken = Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('')

    // Encode tier selection into state for backend to access during OAuth callback
    const stateData = {
      csrf: csrfToken,
      ...(tierId !== undefined && { tier_id: tierId }),
      ...(billingCycle && { billing_cycle: billingCycle })
    }

    return btoa(JSON.stringify(stateData))
  }

  storeOAuthState(state: string, tierId?: number, billingCycle?: 'monthly' | 'yearly'): void {
    if (!this.checkSessionStorageAvailable()) {
      throw new Error('SessionStorage is not available. Please check browser privacy settings.')
    }

    try {
      sessionStorage.setItem('oauth_state', state)
      sessionStorage.setItem('oauth_state_timestamp', Date.now().toString())

      // Also store tier selection separately for frontend use after OAuth redirect
      if (tierId !== undefined) {
        sessionStorage.setItem('selected_tier_id', tierId.toString())
      }
      if (billingCycle) {
        sessionStorage.setItem('selected_billing_cycle', billingCycle)
      }
    } catch (error) {
      logger.error('Failed to store OAuth state:', error)
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

  clearOAuthProcessingFlags(): void {
    // Remove all oauth_processing_* keys from sessionStorage
    // This prevents stale flags from previous login attempts from blocking new attempts
    const keysToRemove: string[] = []
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i)
      if (key && key.startsWith('oauth_processing_')) {
        keysToRemove.push(key)
      }
    }
    keysToRemove.forEach(key => sessionStorage.removeItem(key))
  }

  async initializeGoogleOAuth(tierId?: number, billingCycle?: 'monthly' | 'yearly'): Promise<void> {
    try {
      // Clear any stale OAuth processing flags from previous attempts
      this.clearOAuthProcessingFlags()

      const config = await this.getOAuthConfig()
      const state = this.generateSecureState(tierId, billingCycle)

      const params = new URLSearchParams({
        client_id: config.google_client_id,
        redirect_uri: config.redirect_uri,
        response_type: 'code',
        scope: config.scope,
        access_type: 'offline',
        prompt: 'select_account', // Allow quick re-auth without re-consent for returning users
        state
      })

      const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`
      this.storeOAuthState(state, tierId, billingCycle)
      window.location.href = authUrl

    } catch (error) {
      logger.error('OAuth initialization failed:', error)
      throw new Error('Authentication service unavailable: ' + (error as Error).message)
    }
  }

  // Tokens are stored in secure httpOnly cookies by backend (set during OAuth redirect)
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
    logger.debug('[AUTH SERVICE] getCurrentUser called')
    try {
      // httpOnly cookies are sent automatically with this request
      logger.debug('[AUTH SERVICE] Calling /api/v1/auth/me')
      const response = await apiClient.get<User>('/api/v1/auth/me', true)

      // User data no longer cached in sessionStorage (XSS risk)
      // Cookies are the single source of truth

      logger.debug('[AUTH SERVICE] getCurrentUser success:', response?.email)
      return response

    } catch (error) {
        // Silently handle errors - 401 is expected during OAuth flow and on public pages
        const apiError = error as { status?: number; message?: string }

        logger.error('[AUTH SERVICE] getCurrentUser error:', {
          status: apiError?.status,
          message: apiError?.message,
          fullError: error
        })

        if (apiError?.status === 401) {
          logger.warn('[AUTH SERVICE] 401 error - clearing auth data')
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
      logger.error('Token refresh failed:', error)
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
      logger.error('Logout request failed:', error)
    } finally {
      this.clearTokenRefresh()
      this.clearAllAuthData()
    }
  }

  clearAllAuthData(): void {
    // Clear OAuth state and processing flags
    this.clearStoredOAuthState()
    this.clearOAuthProcessingFlags()

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
      logger.error('Failed to get trial info:', error)
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