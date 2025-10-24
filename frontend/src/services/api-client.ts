// frontend/src/services/api-client.ts

import { ApiResponse, ApiError, RequestConfig } from '@/types/auth.types'

interface ApiClientConfig {
  baseURL: string
  timeout: number
  maxRetries: number
  retryDelay: number
}

export class ApiClient {
  private readonly config: ApiClientConfig
  private requestCounter = 0

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

        // Only log first attempt to avoid spam
        if (attempt === 0) {
          console.log(`[API ${currentRequestId}] ${method} ${url} (attempt ${attempt + 1}/${maxRetries + 1})`)
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

        // Only log errors and successful non-auth requests
        const isExpected401 = response.status === 401 && (endpoint.includes('/auth/me') || endpoint.includes('/auth/refresh'))
        if (!response.ok && !isExpected401) {
          console.log(`[API ${currentRequestId}] Response ${response.status} in ${duration}ms`)
        }

        if (!response.ok) {
          const error = this.createHttpError(response, responseData)

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
          // Only log retries, not every attempt
          if (attempt > 0) {
            console.warn(`[API ${currentRequestId}] Retry ${attempt} failed, retrying:`, (error as Error).message)
          }
          await this.delay(this.config.retryDelay * Math.pow(2, attempt))
          continue
        }

        // Only log final failure, not intermediate attempts
        if (attempt === maxRetries) {
          console.error(`[API ${currentRequestId}] Request failed after ${attempt + 1} attempts:`, error)
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
    
    return {
      name: 'HttpError',
      message: errorData?.message as string || errorData?.detail as string || `HTTP ${response.status}: ${response.statusText}`,
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
    
    // Only retry server errors (500+), timeouts (408), and rate limits (429)
    // Do NOT retry 401 - those should be handled by auth flow, not retried
    return status >= 500 || status === 408 || status === 429
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
}

export const apiClient = new ApiClient()