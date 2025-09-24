// src/services/auth.service.ts
/**
 * Authentication service for Google OAuth and JWT token management
 * Handles all authentication-related API calls and token storage
 */

import { apiClient } from './api-client'
import { TokenResponse, User } from '@/types/auth.types'

interface GoogleOAuthConfig {
  google_client_id: string
  redirect_uri: string
}

export class AuthService {
  private readonly apiUrl: string
  private readonly tokenRefreshPromise: Map<string, Promise<TokenResponse>> = new Map()

  constructor() {
    this.apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  }

  /**
   * Initialize Google OAuth flow
   * Returns the Google OAuth authorization URL
   */
  async initializeGoogleOAuth(): Promise<string> {
    try {
      const config = await this.getOAuthConfig()
      const params = new URLSearchParams({
        client_id: config.google_client_id,
        redirect_uri: config.redirect_uri,
        response_type: 'code',
        scope: 'openid email profile',
        access_type: 'offline',
        prompt: 'consent'
      })

      return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`
    } catch (error) {
      console.error('Failed to initialize Google OAuth:', error)
      throw new Error('Failed to initialize authentication')
    }
  }

  /**
   * Exchange Google OAuth code for JWT tokens
   * Handles first-time user creation with 30-day premium trial
   */
  async exchangeGoogleToken(googleToken: string): Promise<TokenResponse> {
    try {
      const request = { 
        google_token: googleToken,
        new_user_trial: true // Signal backend to provide 30-day trial for new users
      }
      const tokenResponse = await apiClient.post<TokenResponse>('/api/v1/auth/google/callback', request)
      
      // Store tokens immediately after successful exchange
      this.storeTokens({
        access_token: tokenResponse.access_token,
        refresh_token: tokenResponse.refresh_token
      })

      // Store user creation timestamp for trial tracking
      if (tokenResponse.tier === 'trial') {
        this.storeTrialInfo(tokenResponse)
      }
      
      return tokenResponse
    } catch (error) {
      console.error('Google token exchange failed:', error)
      throw error
    }
  }

  /**
   * Refresh JWT tokens using refresh token
   * Implements deduplication to prevent multiple simultaneous refresh requests
   */
  async refreshToken(refreshToken?: string): Promise<TokenResponse> {
    const tokenToRefresh = refreshToken || this.getStoredTokens()?.refresh_token
    
    if (!tokenToRefresh) {
      throw new Error('No refresh token available')
    }

    // Prevent multiple simultaneous refresh requests
    const existingPromise = this.tokenRefreshPromise.get(tokenToRefresh)
    if (existingPromise) {
      return existingPromise
    }

    const refreshPromise = this.performTokenRefresh(tokenToRefresh)
    this.tokenRefreshPromise.set(tokenToRefresh, refreshPromise)

    try {
      const result = await refreshPromise
      return result
    } finally {
      this.tokenRefreshPromise.delete(tokenToRefresh)
    }
  }

  private async performTokenRefresh(refreshToken: string): Promise<TokenResponse> {
    try {
      const request = { refresh_token: refreshToken }
      const tokenResponse = await apiClient.post<TokenResponse>('/api/v1/auth/refresh', request)
      
      // Update stored tokens
      this.storeTokens({
        access_token: tokenResponse.access_token,
        refresh_token: tokenResponse.refresh_token
      })
      
      return tokenResponse
    } catch (error) {
      console.error('Token refresh failed:', error)
      // Clear invalid tokens
      this.clearTokens()
      throw error
    }
  }

  /**
   * Get current authenticated user profile
   */
  async getCurrentUser(): Promise<User> {
    try {
      return await apiClient.get<User>('/api/v1/users/profile', true)
    } catch (error) {
      console.error('Failed to get current user:', error)
      throw error
    }
  }

  /**
   * Logout user and clear tokens
   */
  async logout(): Promise<void> {
    try {
      // Attempt to logout on server
      await apiClient.delete('/api/v1/auth/logout', true)
    } catch (error) {
      console.error('Server logout failed:', error)
      // Continue with local cleanup even if server logout fails
    } finally {
      // Always clear local tokens
      this.clearTokens()
    }
  }

  /**
   * Get Google OAuth configuration from backend
   */
  private async getOAuthConfig(): Promise<GoogleOAuthConfig> {
    try {
      return await apiClient.get<GoogleOAuthConfig>('/api/v1/auth/google/config')
    } catch (error) {
      console.error('Failed to get OAuth config:', error)
      // Fallback configuration using environment variables
      return {
        google_client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
        redirect_uri: `${window.location.origin}/login`
      }
    }
  }

  /**
   * Store JWT tokens in localStorage
   */
  storeTokens(tokens: { access_token: string; refresh_token: string }): void {
    if (typeof window === 'undefined') return
    
    try {
      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
      
      // Store timestamp for token management
      localStorage.setItem('tokens_stored_at', Date.now().toString())
    } catch (error) {
      console.error('Failed to store tokens:', error)
    }
  }

  /**
   * Clear all stored tokens and trial info
   */
  clearTokens(): void {
    if (typeof window === 'undefined') return
    
    try {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('tokens_stored_at')
      localStorage.removeItem('trial_info') // Also clear trial info on logout
    } catch (error) {
      console.error('Failed to clear tokens:', error)
    }
  }

  /**
   * Get stored tokens from localStorage
   */
  getStoredTokens(): { access_token: string; refresh_token: string } | null {
    if (typeof window === 'undefined') return null
    
    try {
      const accessToken = localStorage.getItem('access_token')
      const refreshToken = localStorage.getItem('refresh_token')
      
      if (!accessToken || !refreshToken) return null
      
      return {
        access_token: accessToken,
        refresh_token: refreshToken
      }
    } catch (error) {
      console.error('Failed to get stored tokens:', error)
      return null
    }
  }

  /**
   * Check if tokens are likely expired based on storage time
   * Note: This is a client-side heuristic, server validation is authoritative
   */
  areTokensLikelyExpired(): boolean {
    if (typeof window === 'undefined') return true
    
    try {
      const storedAt = localStorage.getItem('tokens_stored_at')
      if (!storedAt) return true
      
      const storedTime = parseInt(storedAt, 10)
      const now = Date.now()
      const elapsed = now - storedTime
      
      // Consider tokens expired if stored more than 45 minutes ago
      // (assumes 60-minute token expiry with 15-minute buffer)
      return elapsed > 45 * 60 * 1000
    } catch (error) {
      console.error('Failed to check token expiry:', error)
      return true
    }
  }

  /**
   * Store trial information for new users
   */
  private storeTrialInfo(tokenResponse: TokenResponse): void {
    if (typeof window === 'undefined') return

    try {
      const trialInfo = {
        start_date: new Date().toISOString(),
        end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days from now
        tier: tokenResponse.tier,
        user_id: tokenResponse.user_id
      }
      
      localStorage.setItem('trial_info', JSON.stringify(trialInfo))
    } catch (error) {
      console.error('Failed to store trial info:', error)
    }
  }

  /**
   * Get trial information for current user
   */
  getTrialInfo(): { start_date: string; end_date: string; tier: string; user_id: string; days_remaining: number } | null {
    if (typeof window === 'undefined') return null

    try {
      const trialInfoStr = localStorage.getItem('trial_info')
      if (!trialInfoStr) return null

      const trialInfo = JSON.parse(trialInfoStr)
      const endDate = new Date(trialInfo.end_date)
      const now = new Date()
      const daysRemaining = Math.max(0, Math.ceil((endDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)))

      return {
        ...trialInfo,
        days_remaining: daysRemaining
      }
    } catch (error) {
      console.error('Failed to get trial info:', error)
      return null
    }
  }

  /**
   * Check if user is in active trial period
   */
  isTrialActive(): boolean {
    const trialInfo = this.getTrialInfo()
    if (!trialInfo) return false

    const endDate = new Date(trialInfo.end_date)
    return new Date() < endDate
  }

  /**
   * Validate tokens format (basic client-side validation)
   */
  validateTokenFormat(tokens: { access_token: string; refresh_token: string }): boolean {
    try {
      // Basic JWT format validation (three parts separated by dots)
      const accessTokenParts = tokens.access_token.split('.')
      const refreshTokenParts = tokens.refresh_token.split('.')
      
      return accessTokenParts.length === 3 && refreshTokenParts.length === 3
    } catch {
      return false
    }
  }
}

export const authService = new AuthService()