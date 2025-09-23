// src/services/api-client.ts
/**
 * API client for communicating with Bonifatus DMS backend
 * Handles authentication, errors, and request/response formatting
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public details?: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new ApiError(
          response.status,
          errorData.message || response.statusText,
          errorData.details
        )
      }

      // Handle empty responses
      if (response.status === 204) {
        return {} as T
      }

      return await response.json()
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      throw new ApiError(0, 'Network error occurred')
    }
  }

  // Add authorization header for authenticated requests
  private getAuthHeaders(): HeadersInit {
    const token = this.getAccessToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  private getAccessToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('access_token')
  }

  // Public API methods
  async get<T>(endpoint: string, authenticated = false): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'GET',
      headers: authenticated ? this.getAuthHeaders() : {},
    })
  }

  async post<T>(
    endpoint: string,
    data?: Record<string, unknown>,
    authenticated = false
  ): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      headers: authenticated ? this.getAuthHeaders() : {},
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T>(
    endpoint: string,
    data?: Record<string, unknown>,
    authenticated = false
  ): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      headers: authenticated ? this.getAuthHeaders() : {},
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(endpoint: string, authenticated = false): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
      headers: authenticated ? this.getAuthHeaders() : {},
    })
  }

  // Health check endpoint
  async healthCheck(): Promise<{ status: string }> {
    return this.get('/health')
  }
}

export const apiClient = new ApiClient()