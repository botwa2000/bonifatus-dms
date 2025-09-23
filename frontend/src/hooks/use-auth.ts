// frontend/src/hooks/use-auth.ts

'use client';

import { useState, useEffect, useCallback } from 'react';
import { authService } from '../services/auth.service';
import { User, AuthError } from '../types/auth.types';

interface UseAuthReturn {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: AuthError | null;
  login: (googleToken: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
  clearError: () => void;
}

export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<AuthError | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const handleAuthError = useCallback((error: any) => {
    try {
      const parsedError = JSON.parse(error.message);
      setError(parsedError);
    } catch {
      setError({
        error: 'unknown_error',
        message: error.message || 'An unexpected error occurred',
      });
    }
  }, []);

  const login = useCallback(async (googleToken: string) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await authService.authenticateWithGoogle(googleToken);
      setUser(response.user);
      setIsAuthenticated(true);
    } catch (error) {
      handleAuthError(error);
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, [handleAuthError]);

  const logout = useCallback(async () => {
    try {
      setIsLoading(true);
      await authService.logout();
    } catch (error) {
      console.warn('Logout error:', error);
    } finally {
      setUser(null);
      setIsAuthenticated(false);
      setIsLoading(false);
      setError(null);
    }
  }, []);

  const refreshAuth = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const user = await authService.getCurrentUser();
      setUser(user);
      setIsAuthenticated(true);
    } catch (error) {
      handleAuthError(error);
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, [handleAuthError]);

  const initializeAuth = useCallback(async () => {
    try {
      setIsLoading(true);
      
      authService.initializeAuth();
      
      if (authService.isAuthenticated()) {
        const storedUser = authService.getStoredUser();
        if (storedUser) {
          setUser(storedUser);
          setIsAuthenticated(true);
          
          // Verify token is still valid
          try {
            const currentUser = await authService.getCurrentUser();
            setUser(currentUser);
          } catch (error) {
            // Token might be expired, try refresh
            try {
              await authService.refreshAccessToken();
              const currentUser = await authService.getCurrentUser();
              setUser(currentUser);
            } catch (refreshError) {
              // Both failed, clear authentication
              await authService.logout();
              setIsAuthenticated(false);
              setUser(null);
            }
          }
        } else {
          setIsAuthenticated(false);
        }
      } else {
        setIsAuthenticated(false);
      }
    } catch (error) {
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    refreshAuth,
    clearError,
  };
}