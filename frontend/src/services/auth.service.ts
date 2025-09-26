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

interface TrialInfo {
  days_remaining: number
  expires_at: string
  features: string[]
}

export class AuthService {
  private readonly config: AuthServiceConfig
  private tokenRefreshPromise: Promise<TokenResponse> | null = null
  private refreshTimeoutId: NodeJS.Timeout | null = null

  constructor() {
    this.config = {
      apiUrl: process.env.NEXT_PUBLIC_API_URL || 'https://bonifatus-dms-mmdbxdflfa-uc.a.run.app',
      tokenRefreshThreshold: 5 * 60 * 1000,
      maxRetries: 3
    }

    this.initializeTokenRefresh()
  }

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
      
      this.storeOAuthState(params.get('state')!)
      window.location.href = authUrl
      
    } catch (error) {
      console.error('Failed to initialize Google OAuth:', error)
      throw new Error('Authentication service unavailable')
    }
  }

  async exchangeGoogleToken(code: string, state?: string): Promise<TokenResponse> {
    try {
      if (state) {
        this.validateOAuthState(state)
      }

      const tokenResponse = await apiClient.post<TokenResponse>('/api/v1/auth/google/callback', {
        code,
        state
      })

      this.storeTokens(tokenResponse)
      this.scheduleTokenRefresh(tokenResponse.access_token)
      this.clearStoredOAuthState()

      return tokenResponse

    } catch (error) {
      this.clearStoredOAuthState()
      throw this.handleAuthError(error)
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

  async getCurrentUser(): Promise<User | null> {
    try {
      const token = this.getStoredAccessToken()
      if (!token || this.isTokenExpired(token)) {
        const refreshed = await this.refreshTokens()
        if (!refreshed) {
          return null
        }
      }

      const user = await apiClient.get<User>('/api/v1/users/profile', true)
      this.storeUserProfile(user)
      return user

    } catch (error) {
      console.error('Failed to get current user:', error)
      return null
    }
  }

  getTrialInfo(): TrialInfo | null {
    try {
      const user = this.getStoredUserProfile()
      if (!user) return null

      const trialEndDate = new Date(user.created_at)
      trialEndDate.setDate(trialEndDate.getDate() + 30)
      
      const now = new Date()
      const daysRemaining = Math.max(0, Math.ceil((trialEndDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)))

      if (daysRemaining <= 0) return null

      return {
        days_remaining: daysRemaining,
        expires_at: trialEndDate.toISOString(),
        features: ['unlimited_documents', 'ai_search', 'priority_support']
      }

    } catch (error) {
      console.error('Failed to get trial info:', error)
      return null
    }
  }

  isTrialActive(): boolean {
    const trialInfo = this.getTrialInfo()
    return trialInfo !== null && trialInfo.days_remaining > 0
  }

  private async getOAuthConfig(): Promise<GoogleOAuthConfig> {
    return apiClient.get<GoogleOAuthConfig>('/api/v1/auth/google/config')
  }

  private async performTokenRefresh(refreshToken: string): Promise<TokenResponse> {
    return apiClient.post<TokenResponse>('/api/v1/auth/refresh', {
      refresh_token: refreshToken
    })
  }

  private storeTokens(tokenResponse: TokenResponse): void {
    if (typeof window === 'undefined') return

    localStorage.setItem('access_token', tokenResponse.access_token)
    localStorage.setItem('refresh_token', tokenResponse.refresh_token)
    localStorage.setItem('tokens_stored_at', Date.now().toString())
    
    if (tokenResponse.user) {
      this.storeUserProfile(tokenResponse.user)
    }
  }

  private storeUserProfile(user: User): void {
    if (typeof window === 'undefined') return
    localStorage.setItem('user_profile', JSON.stringify(user))
  }

  private getStoredUserProfile(): User | null {
    if (typeof window === 'undefined') return null
    
    try {
      const stored = localStorage.getItem('user_profile')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  }

  private getStoredAccessToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('access_token')
  }

  private getStoredRefreshToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('refresh_token')
  }

  private initializeTokenRefresh(): void {
    if (typeof window === 'undefined') return

    const token = this.getStoredAccessToken()
    if (token && !this.isTokenExpired(token)) {
      this.scheduleTokenRefresh(token)
    }
  }

  private scheduleTokenRefresh(token: string): void {
    try {
      const payload = this.decodeJWTPayload(token)
      const expiresAt = payload.exp * 1000
      const refreshAt = expiresAt - this.config.tokenRefreshThreshold
      const delay = refreshAt - Date.now()

      if (delay > 0) {
        this.refreshTimeoutId = setTimeout(() => {
          this.refreshTokens().catch(error => {
            console.error('Scheduled token refresh failed:', error)
          })
        }, delay)
      }

    } catch (error) {
      console.error('Failed to schedule token refresh:', error)
    }
  }

  private clearTokenRefresh(): void {
    if (this.refreshTimeoutId) {
      clearTimeout(this.refreshTimeoutId)
      this.refreshTimeoutId = null
    }
  }

  private isTokenExpired(token: string): boolean {
    try {
      const payload = this.decodeJWTPayload(token)
      const expiresAt = payload.exp * 1000
      const bufferTime = 5 * 60 * 1000
      
      return Date.now() >= (expiresAt - bufferTime)

    } catch {
      return true
    }
  }

  private validateOAuthState(providedState?: string): void {
    const storedState = this.getStoredOAuthState()
    
    if (!storedState || !providedState || storedState !== providedState) {
      throw new Error('Invalid OAuth state - potential CSRF attack')
    }
  }

  private decodeJWTPayload(token: string): JWTPayload {
    const parts = token.split('.')
    if (parts.length !== 3) {
      throw new Error('Invalid JWT format')
    }
    
    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded) as JWTPayload
  }

  private generateSecureState(): string {
    const array = new Uint8Array(16)
    crypto.getRandomValues(array)
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('')
  }

  private storeOAuthState(state: string): void {
    if (typeof window === 'undefined') return
    sessionStorage.setItem('oauth_state', state)
  }

  private getStoredOAuthState(): string | null {
    if (typeof window === 'undefined') return null
    return sessionStorage.getItem('oauth_state')
  }

  private clearStoredOAuthState(): void {
    if (typeof window === 'undefined') return
    sessionStorage.removeItem('oauth_state')
  }

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

  private handleAuthError(error: unknown): AuthError {
    if (this.isErrorWithResponse(error)) {
      const errorData = this.extractErrorData(error)
      
      return {
        name: 'AuthError',
        message: errorData.message,
        status: errorData.status,
        code: errorData.code,
        details: errorData.details
      }
    }
    
    const errorMessage = error instanceof Error ? error.message : 'Network error occurred'
    
    return {
      name: 'AuthError',
      message: errorMessage,
      code: 'network_error',
      details: 'Unable to communicate with authentication service'
    }
  }

  private isErrorWithResponse(error: unknown): error is { response: { data: Record<string, unknown>; status: number } } {
    return error !== null && 
           typeof error === 'object' && 
           'response' in error && 
           typeof (error as Record<string, unknown>).response === 'object'
  }

  private extractErrorData(error: { response: { data: Record<string, unknown>; status: number } }): {
    message: string
    status: number
    code: string
    details: string
  } {
    const { data, status } = error.response
    
    return {
      message: String(data.message || data.detail || 'Authentication failed'),
      status: status || 0,
      code: String(data.error || 'authentication_failed'),
      details: String(data.details || '')
    }
  }
}

export const authService = new AuthService()