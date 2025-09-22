// src/types/auth.types.ts
/**
 * Authentication types matching backend API responses
 */

export interface User {
  id: string
  email: string
  full_name: string
  profile_picture?: string
  tier: 'free' | 'trial' | 'premium'
  is_active: boolean
  last_login_at?: string
  created_at: string
  updated_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user_id: string
  email: string
  tier: string
}

export interface AuthState {
  user: User | null
  tokens: {
    access_token: string
    refresh_token: string
  } | null
  isAuthenticated: boolean
  isLoading: boolean
}

export interface GoogleTokenRequest {
  google_token: string
}

export interface RefreshTokenRequest {
  refresh_token: string
}