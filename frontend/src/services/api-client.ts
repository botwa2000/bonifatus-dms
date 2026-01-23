// frontend/src/services/api-client.ts

import { ApiResponse, ApiError, RequestConfig } from '@/types/auth.types'
import { logger } from '@/lib/logger'
import { performanceMonitor } from '@/lib/performance'

interface ApiClientConfig {
  baseURL: string
  timeout: number
  maxRetries: number
  retryDelay: number
}

export class ApiClient {
  private readonly config: ApiClientConfig
  private requestCounter = 0
  private isRefreshing = false
  private refreshPromise: Promise<boolean> | null = null

  constructor() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL

    if (!apiUrl) {
      throw new Error('NEXT_PUBLIC_API_URL must be set in environment variables')
    }

    this.config = {
      baseURL: apiUrl,
      timeout: 30000,
      maxRetries: 3,
      retryDelay: 1000
    }

    this.config.baseURL = this.config.baseURL.replace(/\/$/, '')
  }

  async get<T = unknown>(
    endpoint: string, 
    requireAuth = false, 
    config?: RequestConfig
  ): Promise<T> {
    return this.request<T>('GET', endpoint, undefined, requireAuth, config)
  }

  async post<T = unknown>(
    endpoint: string, 
    data?: unknown, 
    requireAuth = false, 
    config?: RequestConfig
  ): Promise<T> {
    return this.request<T>('POST', endpoint, data, requireAuth, config)
  }

  async put<T = unknown>(
    endpoint: string, 
    data?: unknown, 
    requireAuth = false, 
    config?: RequestConfig
  ): Promise<T> {
    return this.request<T>('PUT', endpoint, data, requireAuth, config)
  }

  async delete<T = unknown>(
    endpoint: string, 
    requireAuth = false, 
    config?: RequestConfig
  ): Promise<T> {
    return this.request<T>('DELETE', endpoint, undefined, requireAuth, config)
  }

  async patch<T = unknown>(
    endpoint: string, 
    data?: unknown, 
    requireAuth = false, 
    config?: RequestConfig
  ): Promise<T> {
    return this.request<T>('PATCH', endpoint, data, requireAuth, config)
  }

  private async request<T>(
    method: string,
    endpoint: string,
    data?: unknown,
    requireAuth = false,
    config: RequestConfig = {}
  ): Promise<T> {
    const currentRequestId = ++this.requestCounter
    const requestId = Math.random().toString(36).substr(2, 9)
    const startTime = Date.now()

    const maxRetries = config.retries ?? this.config.maxRetries
    let lastError: Error | null = null

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const url = this.buildUrl(endpoint, config.params)
        const headers = await this.buildHeaders(requireAuth, config.headers)

        const requestConfig: RequestInit = {
          method,
          headers,
          credentials: 'include'  // Include cookies in cross-origin requests
          // Removed AbortSignal - it was causing premature aborts on slow connections
        }

        if (data && method !== 'GET' && method !== 'DELETE') {
          requestConfig.body = JSON.stringify(data)
        }

        const response = await fetch(url, requestConfig)
        const responseHeaders = this.parseHeaders(response.headers)

        let responseData: unknown
        const contentType = response.headers.get('content-type')

        if (contentType?.includes('application/json')) {
          responseData = await response.json()
        } else {
          responseData = await response.text()
        }

        const duration = Date.now() - startTime

        // Record performance metric
        const responseRequestId = response.headers.get('X-Request-ID') || undefined
        performanceMonitor.recordApiCall(
          endpoint,
          method,
          duration,
          response.status,
          responseRequestId
        )

        if (!response.ok) {
          const error = this.createHttpError(response, responseData)

          logger.error('[API CLIENT] HTTP error:', {
            status: response.status,
            endpoint,
            requireAuth,
            error: error.message
          })

          // Handle 401 errors with automatic token refresh (except for refresh endpoint itself)
          if (response.status === 401 && !endpoint.includes('/auth/refresh') && requireAuth) {
            logger.warn('[API CLIENT] 401 error - attempting token refresh')
            const refreshed = await this.refreshToken()
            if (refreshed) {
              logger.debug('[API CLIENT] Token refresh successful - retrying request')
              // Token refreshed successfully, retry the request once
              lastError = error
              continue
            }
            // Refresh failed, redirect to login
            logger.error('[API CLIENT] Token refresh failed - redirecting to /login')
            if (typeof window !== 'undefined') {
              window.location.href = '/login'
            }
            throw error
          }

          if (this.shouldRetry(response.status, attempt, maxRetries)) {
            lastError = error
            await this.delay(this.config.retryDelay * Math.pow(2, attempt))
            continue
          }

          throw error
        }

        const apiResponse: ApiResponse<T> = {
          data: responseData as T,
          status: response.status,
          statusText: response.statusText,
          headers: responseHeaders
        }

        return apiResponse.data

      } catch (error) {
        lastError = error as Error

        if (this.isRetriableError(error as Error) && attempt < maxRetries) {
          await this.delay(this.config.retryDelay * Math.pow(2, attempt))
          continue
        }

        throw this.normalizeError(error as Error)
      }
    }

    throw this.normalizeError(lastError || new Error('Unknown error occurred'))
  }

  private buildUrl(endpoint: string, params?: Record<string, string | number | boolean>): string {
    const baseUrl = this.config.baseURL
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
    
    const fullUrl = `${baseUrl}${cleanEndpoint}`
    
    if (!params || Object.keys(params).length === 0) {
      return fullUrl
    }
    
    const queryParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value))
      }
    })
    
    const queryString = queryParams.toString()
    return queryString ? `${fullUrl}?${queryString}` : fullUrl
  }

  private async buildHeaders(
    _requireAuth = false,
    customHeaders: Record<string, string> = {}
  ): Promise<Record<string, string>> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...customHeaders
    }

    // Tokens are in httpOnly cookies, no Authorization header needed
    // Cookies are sent automatically with credentials: 'include'
    // _requireAuth parameter kept for API compatibility but not used

    // Add X-Acting-As-User-Id header if user is acting as delegate
    if (typeof window !== 'undefined') {
      const actingAsUserId = localStorage.getItem('actingAsUserId')
      if (actingAsUserId) {
        headers['X-Acting-As-User-Id'] = actingAsUserId
      }
    }

    return headers
  }

  private parseHeaders(headers: Headers): Record<string, string> {
    const headerObj: Record<string, string> = {}
    headers.forEach((value, key) => {
      headerObj[key] = value
    })
    return headerObj
  }

  private getStoredAccessToken(): string | null {
    // Tokens are in httpOnly cookies, not accessible via JavaScript
    // This method is kept for compatibility but returns null
    return null
  }

  private createTimeoutSignal(timeout?: number): AbortSignal {
    const controller = new AbortController()
    const timeoutMs = timeout ?? this.config.timeout
    
    setTimeout(() => controller.abort(), timeoutMs)
    
    return controller.signal
  }

  private createHttpError(response: Response, data: unknown): ApiError {
    const errorData = data as Record<string, unknown>

    // Extract error message
    let message: string
    if (errorData?.message && typeof errorData.message === 'string') {
      message = errorData.message
    } else if (errorData?.detail) {
      // Handle structured detail objects (e.g., { code: "...", message: "..." })
      if (typeof errorData.detail === 'object' && errorData.detail !== null) {
        const detailObj = errorData.detail as Record<string, unknown>
        message = (detailObj.message as string) || `HTTP ${response.status}: ${response.statusText}`
      } else if (typeof errorData.detail === 'string') {
        message = errorData.detail
      } else {
        message = `HTTP ${response.status}: ${response.statusText}`
      }
    } else {
      message = `HTTP ${response.status}: ${response.statusText}`
    }

    return {
      name: 'HttpError',
      message,
      status: response.status,
      response: {
        data: errorData,
        status: response.status,
        statusText: response.statusText
      }
    } as ApiError
  }

  private shouldRetry(status: number, attempt: number, maxRetries: number): boolean {
    if (attempt >= maxRetries) return false

    // Only retry timeouts (408) and rate limits (429)
    // Do NOT retry 401 (auth errors) or 500+ (server errors should fail fast)
    return status === 408 || status === 429
  }

  private isRetriableError(error: Error): boolean {
    return error.name === 'TypeError' || error.name === 'AbortError'
  }

  private normalizeError(error: Error): ApiError {
    const apiError: ApiError = {
      name: 'ApiError',
      message: error.message || 'Unknown error occurred'
    }

    const errorWithCause = error as Error & { cause?: Record<string, unknown> }
    
    if (errorWithCause.cause && typeof errorWithCause.cause === 'object') {
      const cause = errorWithCause.cause
      
      if (cause.status) {
        apiError.status = cause.status as number
      }
      
      if (cause.statusText || cause.data) {
        apiError.response = {
          status: cause.status as number,
          statusText: cause.statusText as string,
          data: cause.data as Record<string, unknown>
        }
      }
    }

    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      apiError.message = 'Network error - please check your internet connection'
    }

    return apiError
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  private async refreshToken(): Promise<boolean> {
    // If a refresh is already in progress, wait for it
    if (this.isRefreshing && this.refreshPromise) {
      return this.refreshPromise
    }

    this.isRefreshing = true
    this.refreshPromise = (async () => {
      try {
        const url = `${this.config.baseURL}/api/v1/auth/refresh`
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          credentials: 'include', // Send refresh token cookie
          body: JSON.stringify({}) // Empty body, token comes from cookie
        })

        if (response.ok) {
          logger.debug('[API Client] Token refreshed successfully')
          return true
        }

        logger.warn('[API Client] Token refresh failed:', response.status)
        return false
      } catch (error) {
        logger.error('[API Client] Token refresh error:', error)
        return false
      } finally {
        this.isRefreshing = false
        this.refreshPromise = null
      }
    })()

    return this.refreshPromise
  }
}

export const apiClient = new ApiClient()