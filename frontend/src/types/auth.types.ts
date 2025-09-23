// frontend/src/types/auth.types.ts

export interface User {
  id: string;
  email: string;
  full_name: string;
  profile_picture?: string;
  tier: string;
  is_active: boolean;
  last_login_at?: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthError {
  error: string;
  message: string;
  details?: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: AuthError | null;
}

export interface GoogleTokenRequest {
  google_token: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}