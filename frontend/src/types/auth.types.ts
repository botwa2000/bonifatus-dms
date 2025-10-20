// frontend/src/types/auth.types.ts

export interface User {
  id: string
  email: string
  full_name: string
  profile_picture?: string
  tier: string
  created_at: string
  updated_at: string
  last_login?: string
  is_active: boolean
}

export interface TrialInfo {
  days_remaining: number
  expires_at: string
  features: string[]
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user_id: string
  email: string
  full_name: string
  profile_picture?: string
  tier: string
  is_active: boolean
}

export interface RefreshTokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  expires_at: number
}

export interface GoogleOAuthConfig {
  google_client_id: string
  redirect_uri: string
  scope: string
}

export interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

export interface AuthError extends Error {
  status?: number
  code?: string
  details?: string
}

export interface LoginRequest {
  code: string
  state?: string
}

export interface LogoutRequest {
  refresh_token?: string
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface ApiError extends Error {
  status?: number
  code?: string
  details?: string
  response?: {
    data?: Record<string, unknown>
    status?: number
    statusText?: string
  }
  request?: Record<string, unknown>
}

export interface RequestConfig {
  headers?: Record<string, string>
  params?: Record<string, string>
  timeout?: number
  retries?: number
}

export interface ApiResponse<T = unknown> {
  data: T
  status: number
  statusText: string
  headers: Record<string, string>
}