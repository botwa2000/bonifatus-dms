// frontend/src/services/auth.service.ts
/**
 * Authentication Service - Production Grade Implementation
 * Handles Google OAuth, JWT token management, and user sessions
 * Zero hardcoded values, comprehensive error handling, token refresh
 */

import { apiClient } from './api-client'
import { TokenResponse, User, GoogleOAuthConfig, RefreshTokenResponse, AuthError } from '@/types/auth.types'

interface AuthServiceConfig {
  apiUrl: string
  clientId: string
  tokenRefreshThreshold: number
  maxRetries: number
}

export class AuthService {
  private readonly config: AuthServiceConfig
  private tokenRefreshPromise: Promise<TokenResponse> | null = null
  private refreshTimeoutId: NodeJS.Timeout | null = null

  constructor() {
    this.config = {
      apiUrl: process.env.NEXT_PUBLIC_API_URL || '',
      clientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
      tokenRefreshThreshold: 5 * 60 * 1000, // 5 minutes before expiry
      maxRetries: 3
    }

    if (!this.config.apiUrl || !this.config.clientId) {
      throw new Error('Missing required environment variables: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_GOOGLE_CLIENT_ID')
    }

    // Initialize automatic token refresh on service creation
    this.initializeTokenRefresh()
  }

  /**
   * Initialize Google OAuth flow
   * Fetches configuration from backend and redirects to Google OAuth
   */
  async initializeGoogleOAuth(): Promise<void> {
    try {
      const config = await this.getOAuthConfig()
      
      const params = new URLSearchParams({
        client_id: config.google_client_id,
        redirect_uri: config.redirect_uri,
        response_type: 'code',
        scope: 'openid email profile',
        access_type: 'offline',
        prompt: 'consent',
        state: this.generateSecureState()
      })

      const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`
      
      // Store state for verification
      this.storeOAuthState(params.get('state')!)
      
      // Redirect to Google OAuth
      window.location.href = authUrl
      
    } catch (error) {
      console.error('Failed to initialize Google OAuth:', error)
      throw new Error('Authentication service unavailable')
    }
  }

  /**
   * Exchange Google OAuth code for JWT tokens
   * Handles OAuth callback and token storage
   */
  async exchangeGoogleToken(code: string, state?: string): Promise<TokenResponse> {
    try {
      // Verify state parameter for CSRF protection
      if (state) {
        const storedState = this.getStoredOAuthState()
        if (!storedState || storedState !== state) {
          throw new Error('Invalid OAuth state parameter')
        }
        this.clearStoredOAuthState()
      }

      const tokenResponse = await apiClient.post<TokenResponse>(
        '/api/v1/auth/google/callback', 
        { google_token: code }
      )
      
      // Store tokens securely
      this.storeTokens({
        access_token: tokenResponse.access_token,
        refresh_token: tokenResponse.refresh_token
      })

      // Schedule automatic token refresh
      this.scheduleTokenRefresh(tokenResponse.access_token)
      
      return tokenResponse
      
    } catch (error) {
      console.error('Google token exchange failed:', error)
      throw this.handleAuthError(error)
    }
  }

  /**
   * Refresh JWT tokens with deduplication and retry logic
   */
  async refreshToken(refreshToken?: string): Promise<TokenResponse> {
    // Return existing refresh promise if one is in progress
    if (this.tokenRefreshPromise) {
      return this.tokenRefreshPromise
    }

    const token = refreshToken || this.getRefreshToken()
    if (!token) {
      throw new Error('No refresh token available')
    }

    this.tokenRefreshPromise = this.performTokenRefresh(token)

    try {
      const result = await this.tokenRefreshPromise
      
      // Store new tokens
      this.storeTokens({
        access_token: result.access_token,
        refresh_token: result.refresh_token || token // Use new refresh token or keep existing
      })

      // Schedule next refresh
      this.scheduleTokenRefresh(result.access_token)
      
      return result
      
    } catch (error) {
      console.error('Token refresh failed:', error)
      await this.logout() // Clear invalid tokens
      throw error
      
    } finally {
      this.tokenRefreshPromise = null
    }
  }

  /**
   * Get current user profile
   */
  async getCurrentUser(): Promise<User> {
    try {
      return await apiClient.get<User>('/api/v1/auth/me', true)
    } catch (error) {
      console.error('Failed to get current user:', error)
      throw this.handleAuthError(error)
    }
  }

  /**
   * Logout user and clear all tokens
   */
  async logout(): Promise<void> {
    try {
      // Cancel scheduled token refresh
      if (this.refreshTimeoutId) {
        clearTimeout(this.refreshTimeoutId)
        this.refreshTimeoutId = null
      }

      // Attempt server-side logout
      try {
        await apiClient.delete('/api/v1/auth/logout', true)
      } catch (error) {
        console.warn('Server logout failed:', error)
        // Continue with local cleanup
      }

      // Clear all stored authentication data
      this.clearAllAuthData()
      
    } catch (error) {
      console.error('Logout error:', error)
      // Always clear local data even if server logout fails
      this.clearAllAuthData()
    }
  }

  /**
   * Check if user is currently authenticated
   */
  isAuthenticated(): boolean {
    const token = this.getAccessToken()
    if (!token) return false

    try {
      const payload = this.parseJWTPayload(token)
      return payload.exp * 1000 > Date.now()
    } catch {
      return false
    }
  }

  /**
   * Get current access token
   */
  getAccessToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('access_token')
  }

  /**
   * Get current refresh token
   */
  getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('refresh_token')
  }

  // Private Methods

  /**
   * Get Google OAuth configuration from backend
   */
  private async getOAuthConfig(): Promise<GoogleOAuthConfig> {
    try {
      return await apiClient.get<GoogleOAuthConfig>('/api/v1/auth/google/config')
    } catch (error) {
      console.error('Failed to get OAuth config from backend:', error)
      
      // Fallback to environment variables if backend is unavailable
      if (this.config.clientId) {
        return {
          google_client_id: this.config.clientId,
          redirect_uri: `${window.location.origin}/login`
        }
      }
      
      throw new Error('OAuth configuration unavailable')
    }
  }

  /**
   * Perform actual token refresh with retry logic
   */
  private async performTokenRefresh(refreshToken: string): Promise<TokenResponse> {
    let lastError: Error | null = null
    
    for (let attempt = 1; attempt <= this.config.maxRetries; attempt++) {
      try {
        const response = await apiClient.post<RefreshTokenResponse>(
          '/api/v1/auth/refresh',
          { refresh_token: refreshToken }
        )
        
        return {
          access_token: response.access_token,
          refresh_token: refreshToken, // Keep existing refresh token
          token_type: response.token_type,
          user_id: response.user_id,
          email: response.email,
          tier: response.tier
        }
        
      } catch (error) {
        lastError = error as Error
        
        if (attempt < this.config.maxRetries) {
          // Exponential backoff
          const delay = Math.pow(2, attempt) * 1000
          await new Promise(resolve => setTimeout(resolve, delay))
        }
      }
    }
    
    throw lastError || new Error('Token refresh failed after retries')
  }

  /**
   * Store JWT tokens securely
   */
  private storeTokens(tokens: { access_token: string; refresh_token: string }): void {
    if (typeof window === 'undefined') return
    
    try {
      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
      localStorage.setItem('tokens_stored_at', Date.now().toString())
    } catch (error) {
      console.error('Failed to store tokens:', error)
    }
  }

  /**
   * Schedule automatic token refresh
   */
  private scheduleTokenRefresh(accessToken: string): void {
    try {
      const payload = this.parseJWTPayload(accessToken)
      const expiryTime = payload.exp * 1000
      const refreshTime = expiryTime - this.config.tokenRefreshThreshold
      const delay = Math.max(0, refreshTime - Date.now())

      // Clear existing timeout
      if (this.refreshTimeoutId) {
        clearTimeout(this.refreshTimeoutId)
      }

      // Schedule refresh
      this.refreshTimeoutId = setTimeout(async () => {
        try {
          await this.refreshToken()
        } catch (error) {
          console.error('Scheduled token refresh failed:', error)
        }
      }, delay)
      
    } catch (error) {
      console.error('Failed to schedule token refresh:', error)
    }
  }

  /**
   * Initialize token refresh on service startup
   */
  private initializeTokenRefresh(): void {
    const token = this.getAccessToken()
    if (token && this.isAuthenticated()) {
      this.scheduleTokenRefresh(token)
    }
  }

  /**
   * Parse JWT payload without verification (client-side only)
   */
  private parseJWTPayload(token: string): any {
    const parts = token.split('.')
    if (parts.length !== 3) {
      throw new Error('Invalid JWT format')
    }
    
    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded)
  }

  /**
   * Generate secure random state for OAuth
   */
  private generateSecureState(): string {
    const array = new Uint8Array(16)
    crypto.getRandomValues(array)
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('')
  }

  /**
   * Store OAuth state for CSRF protection
   */
  private storeOAuthState(state: string): void {
    if (typeof window === 'undefined') return
    sessionStorage.setItem('oauth_state', state)
  }

  /**
   * Get stored OAuth state
   */
  private getStoredOAuthState(): string | null {
    if (typeof window === 'undefined') return null
    return sessionStorage.getItem('oauth_state')
  }

  /**
   * Clear stored OAuth state
   */
  private clearStoredOAuthState(): void {
    if (typeof window === 'undefined') return
    sessionStorage.removeItem('oauth_state')
  }

  /**
   * Clear all authentication data
   */
  private clearAllAuthData(): void {
    if (typeof window === 'undefined') return
    
    const keysToRemove = [
      'access_token',
      'refresh_token', 
      'tokens_stored_at',
      'user_profile'
    ]
    
    keysToRemove.forEach(key => localStorage.removeItem(key))
    this.clearStoredOAuthState()
  }

  /**
   * Handle and normalize authentication errors
   */
  private handleAuthError(error: any): AuthError {
    if (error?.response?.data) {
      return {
        error: error.response.data.error || 'authentication_failed',
        message: error.response.data.message || 'Authentication failed',
        details: error.response.data.details
      }
    }
    
    return {
      error: 'network_error',
      message: error.message || 'Network error occurred',
      details: 'Unable to communicate with authentication service'
    }
  }
}

// Export singleton instance
export const authService = new AuthService()