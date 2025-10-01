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
  private tokenRefreshPromise: Promise<TokenResponse> | null = null
  private refreshTimeoutId: NodeJS.Timeout | null = null

  constructor() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL
    
    if (!apiUrl) {
      throw new Error('NEXT_PUBLIC_API_URL environment variable is required. Create frontend/.env.local with NEXT_PUBLIC_API_URL=https://bonifatus-dms-vpm3xabjwq-uc.a.run.app')
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
    try {
      const response = await apiClient.get<{ google_client_id: string; redirect_uri: string }>('/api/v1/auth/google/config')
      
      return {
        google_client_id: response.google_client_id,
        redirect_uri: response.redirect_uri,
        scope: 'openid email profile'
      }
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
  

  async exchangeGoogleToken(code: string, state?: string | null): Promise<{ success: boolean; error?: string }> {
    try {
      // Validate state if provided
      if (state && !this.validateOAuthState(state)) {
        throw new Error('Invalid OAuth state - possible security issue')
      }

      // Exchange authorization code for JWT tokens via backend
      const response = await apiClient.post<{
        access_token: string
        refresh_token: string
        user: User
        expires_at: string
      }>('/api/v1/auth/google/callback', {
        code,
        state: state || ''
      })

      // Store tokens securely
      if (typeof window !== 'undefined') {
        // Store in httpOnly cookies via backend or localStorage for development
        localStorage.setItem('access_token', response.access_token)
        localStorage.setItem('refresh_token', response.refresh_token)
        localStorage.setItem('user', JSON.stringify(response.user))
        localStorage.setItem('expires_at', response.expires_at)
      }

      // Clear OAuth state
      this.clearStoredOAuthState()

      // Initialize token refresh
      this.initializeTokenRefresh()

      return { success: true }

    } catch (error) {
      console.error('Token exchange failed:', error)
      this.clearStoredOAuthState()
      
      const errorMessage = error instanceof Error ? error.message : 'Authentication failed'
      return { success: false, error: errorMessage }
    }
  }

  storeTokens(tokenResponse: TokenResponse): void {
    if (!this.isClientSide()) return
    
    const { access_token, refresh_token, expires_in } = tokenResponse
    
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    localStorage.setItem('token_expires_at', (Date.now() + expires_in * 1000).toString())
    
    document.cookie = `bonifatus_has_token=true; path=/; max-age=${expires_in}; SameSite=Strict; Secure`
  }

  getStoredAccessToken(): string | null {
    if (!this.isClientSide()) return null
    return localStorage.getItem('access_token')
  }

  getStoredRefreshToken(): string | null {
    if (!this.isClientSide()) return null
    return localStorage.getItem('refresh_token')
  }

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
      const token = this.getStoredAccessToken()
      
      if (!token) {
        return null
      }

      if (this.isTokenExpired(token)) {
        const refreshed = await this.refreshTokens()
        if (!refreshed) {
          return null
        }
      }

      const response = await apiClient.get<User>('/api/v1/auth/me', true)
      return response

    } catch (error) {
      console.error('Failed to get current user:', error)
      this.clearAllAuthData()
      return null
    }
  }

  async refreshTokens(): Promise<boolean> {
    if (this.tokenRefreshPromise) {
      try {
        await this.tokenRefreshPromise
        return true
      } catch {
        return false
      }
    }

    const refreshToken = this.getStoredRefreshToken()
    if (!refreshToken) {
      this.clearAllAuthData()
      return false
    }

    try {
      this.tokenRefreshPromise = this.performTokenRefresh(refreshToken)
      const tokenResponse = await this.tokenRefreshPromise
      
      this.storeTokens(tokenResponse)
      this.scheduleTokenRefresh(tokenResponse.access_token)
      
      return true

    } catch (error) {
      console.error('Token refresh failed:', error)
      this.clearAllAuthData()
      return false
    } finally {
      this.tokenRefreshPromise = null
    }
  }

  private async performTokenRefresh(refreshToken: string): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>('/api/v1/auth/refresh', {
      refresh_token: refreshToken
    })
    
    return response
  }

  scheduleTokenRefresh(accessToken: string): void {
    this.clearTokenRefresh()
    
    try {
      const payload = this.decodeJWTPayload(accessToken)
      const expiresIn = payload.exp * 1000 - Date.now()
      const refreshIn = Math.max(expiresIn - this.config.tokenRefreshThreshold, 60000)
      
      this.refreshTimeoutId = setTimeout(() => {
        this.refreshTokens().catch(error => {
          console.error('Scheduled token refresh failed:', error)
        })
      }, refreshIn)
      
    } catch (error) {
      console.error('Failed to schedule token refresh:', error)
    }
  }

  clearTokenRefresh(): void {
    if (this.refreshTimeoutId) {
      clearTimeout(this.refreshTimeoutId)
      this.refreshTimeoutId = null
    }
  }

  initializeTokenRefresh(): void {
    const token = this.getStoredAccessToken()
    if (token && !this.isTokenExpired(token)) {
      this.scheduleTokenRefresh(token)
    }
  }

  async logout(): Promise<void> {
    try {
      const refreshToken = this.getStoredRefreshToken()
      
      if (refreshToken) {
        await apiClient.post('/api/v1/auth/logout', {
          refresh_token: refreshToken
        }, true)
      }

    } catch (error) {
      console.error('Logout request failed:', error)
    } finally {
      this.clearTokenRefresh()
      this.clearAllAuthData()
    }
  }

  clearAllAuthData(): void {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('token_expires_at')
    
    document.cookie = 'bonifatus_has_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Strict; Secure'
    
    this.clearStoredOAuthState()
    this.clearTokenRefresh()
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