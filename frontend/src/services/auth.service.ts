// frontend/src/services/auth.service.ts

import { apiClient } from './api-client';
import {
  TokenResponse,
  RefreshTokenResponse,
  GoogleTokenRequest,
  RefreshTokenRequest,
  User,
  AuthError
} from '../types/auth.types';

class AuthService {
  private readonly STORAGE_ACCESS_TOKEN = 'bonifatus_access_token';
  private readonly STORAGE_REFRESH_TOKEN = 'bonifatus_refresh_token';
  private readonly STORAGE_USER = 'bonifatus_user';

  async authenticateWithGoogle(googleToken: string): Promise<TokenResponse> {
    try {
      const request: GoogleTokenRequest = { google_token: googleToken };
      const response = await apiClient.post<TokenResponse>('/api/v1/auth/google/callback', request);
      
      this.storeTokens(response.access_token, response.refresh_token);
      this.storeUser(response.user);
      apiClient.setAccessToken(response.access_token);
      
      return response;
    } catch (error) {
      this.handleAuthError(error);
      throw error;
    }
  }

  async refreshAccessToken(): Promise<string> {
    try {
      const refreshToken = this.getRefreshToken();
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const request: RefreshTokenRequest = { refresh_token: refreshToken };
      const response = await apiClient.post<RefreshTokenResponse>('/api/v1/auth/refresh', request);
      
      this.storeTokens(response.access_token, refreshToken);
      apiClient.setAccessToken(response.access_token);
      
      return response.access_token;
    } catch (error) {
      this.clearTokens();
      throw error;
    }
  }

  async getCurrentUser(): Promise<User> {
    try {
      return await apiClient.get<User>('/api/v1/auth/me');
    } catch (error) {
      this.handleAuthError(error);
      throw error;
    }
  }

  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/v1/auth/logout');
    } catch (error) {
      console.warn('Logout request failed:', error);
    } finally {
      this.clearTokens();
      apiClient.setAccessToken(null);
    }
  }

  getAccessToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(this.STORAGE_ACCESS_TOKEN);
  }

  getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(this.STORAGE_REFRESH_TOKEN);
  }

  getStoredUser(): User | null {
    if (typeof window === 'undefined') return null;
    const userData = localStorage.getItem(this.STORAGE_USER);
    if (!userData) return null;
    
    try {
      return JSON.parse(userData);
    } catch {
      return null;
    }
  }

  isAuthenticated(): boolean {
    return !!(this.getAccessToken() && this.getRefreshToken());
  }

  initializeAuth(): void {
    const accessToken = this.getAccessToken();
    if (accessToken) {
      apiClient.setAccessToken(accessToken);
    }
  }

  private storeTokens(accessToken: string, refreshToken: string): void {
    if (typeof window === 'undefined') return;
    
    localStorage.setItem(this.STORAGE_ACCESS_TOKEN, accessToken);
    localStorage.setItem(this.STORAGE_REFRESH_TOKEN, refreshToken);
  }

  private storeUser(user: User): void {
    if (typeof window === 'undefined') return;
    
    localStorage.setItem(this.STORAGE_USER, JSON.stringify(user));
  }

  private clearTokens(): void {
    if (typeof window === 'undefined') return;
    
    localStorage.removeItem(this.STORAGE_ACCESS_TOKEN);
    localStorage.removeItem(this.STORAGE_REFRESH_TOKEN);
    localStorage.removeItem(this.STORAGE_USER);
  }

  private handleAuthError(error: any): void {
    if (error.message) {
      try {
        const parsedError = JSON.parse(error.message);
        if (parsedError.error === 'token_expired' || parsedError.error === 'invalid_token') {
          this.clearTokens();
        }
      } catch {
        // Error message is not JSON, ignore
      }
    }
  }

  async withTokenRefresh<T>(operation: () => Promise<T>): Promise<T> {
    try {
      return await operation();
    } catch (error: any) {
      if (error.message) {
        try {
          const parsedError = JSON.parse(error.message);
          if (parsedError.error === 'token_expired') {
            await this.refreshAccessToken();
            return await operation();
          }
        } catch {
          // Error message is not JSON, re-throw original error
        }
      }
      throw error;
    }
  }
}

export const authService = new AuthService();