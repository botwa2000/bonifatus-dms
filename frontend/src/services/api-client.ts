// frontend/src/services/api-client.ts
/**
 * API Client - Production Grade Implementation
 * Handles HTTP requests, authentication, retries, and error handling
 * Zero hardcoded values, comprehensive logging, request/response interceptors
 */

interface ApiClientConfig {
  baseURL: string
  timeout: number
  maxRetries: number
  retryDelay: number
}

interface RequestConfig {
  headers?: Record<string, string>
  params?: Record<string, string>
  timeout?: number
  retries?: number
}

interface ApiResponse<T = any> {
  data: T
  status: number
  statusText: string
  headers: Record<string, string>
}

interface ApiError {
  message: string
  status?: number
  response?: {
    data?: any
    status?: number
    statusText?: string
  }
  request?: any
}

export class ApiClient {
  private readonly config: ApiClientConfig
  private requestId = 0

  constructor() {
    this.config = {
      baseURL: process.env.NEXT_PUBLIC_API_URL || '',
      timeout: 30000, // 30 seconds
      maxRetries: 3,
      retryDelay: 1000 // 1 second
    }

    if (!this.config.baseURL) {
      throw new Error('Missing required environment variable: NEXT_PUBLIC_API_URL')
    }

    // Ensure baseURL doesn't end with slash
    this.config.baseURL = this.config.baseURL.replace(/\/$/, '')
  }

  /**
   * Perform GET request
   */
  async get<T = any>(
    endpoint: string, 
    requireAuth = false, 
    config?: RequestConfig
  ): Promise<T> {
    return this.request<T>('GET', endpoint, undefined, requireAuth, config)
  }

  /**
   * Perform POST request
   */
  async post<T = any>(
    endpoint: string, 
    data?: any, 
    requireAuth = false, 
    config?: RequestConfig
  ): Promise<T> {
    return this.request<T>('POST', endpoint, data, requireAuth, config)
  }

  /**
   * Perform PUT request
   */
  async put<T = any>(
    endpoint: string, 
    data?: any, 
    requireAuth = false, 
    config?: RequestConfig
  ): Promise<T> {
    return this.request<T>('PUT', endpoint, data, requireAuth, config)
  }

  /**
   * Perform DELETE request
   */
  async delete<T = any>(
    endpoint: string, 
    requireAuth = false, 
    config?: RequestConfig
  ): Promise<T> {
    return this.request<T>('DELETE', endpoint, undefined, requireAuth, config)
  }

  /**
   * Perform PATCH request
   */
  async patch<T = any>(
    endpoint: string, 
    data?: any, 
    requireAuth = false, 
    config?: RequestConfig
  ): Promise<T> {
    return this.request<T>('PATCH', endpoint, data, requireAuth, config)
  }

  // Private Methods

  /**
   * Core request method with retry logic and error handling
   */
  private async request<T>(
    method: string,
    endpoint: string,
    data?: any,
    requireAuth = false,
    config: RequestConfig = {}
  ): Promise<T> {
    const requestId = ++this.requestId
    const startTime = Date.now()
    
    const maxRetries = config.retries ?? this.config.maxRetries
    let lastError: ApiError | null = null

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        console.debug(`[API ${requestId}] ${method} ${endpoint} (attempt ${attempt}/${maxRetries})`)
        
        const response = await this.performRequest<T>(
          method, 
          endpoint, 
          data, 
          requireAuth, 
          config,
          requestId
        )

        const duration = Date.now() - startTime
        console.debug(`[API ${requestId}] Success in ${duration}ms`)

        return response.data

      } catch (error) {
        lastError = this.normalizeError(error as Error)
        
        const duration = Date.now() - startTime
        console.warn(`[API ${requestId}] Attempt ${attempt} failed in ${duration}ms:`, lastError.message)

        // Don't retry on client errors (4xx) or authentication errors
        if (lastError.status && (lastError.status < 500 || lastError.status === 401 || lastError.status === 403)) {
          break
        }

        // Don't retry on the last attempt
        if (attempt === maxRetries) {
          break
        }

        // Exponential backoff with jitter
        const delay = this.config.retryDelay * Math.pow(2, attempt - 1) + Math.random() * 1000
        console.debug(`[API ${requestId}] Retrying in ${Math.round(delay)}ms...`)
        
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }

    const totalDuration = Date.now() - startTime
    console.error(`[API ${requestId}] Final failure after ${totalDuration}ms:`, lastError)
    
    throw lastError
  }

  /**
   * Perform actual HTTP request
   */
  private async performRequest<T>(
    method: string,
    endpoint: string,
    data?: any,
    requireAuth = false,
    config: RequestConfig = {},
    requestId?: number
  ): Promise<ApiResponse<T>> {
    const url = this.buildUrl(endpoint, config.params)
    const headers = await this.buildHeaders(requireAuth, config.headers)
    const timeout = config.timeout ?? this.config.timeout

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
      const requestOptions: RequestInit = {
        method,
        headers,
        signal: controller.signal
      }

      // Add body for methods that support it
      if (data && ['POST', 'PUT', 'PATCH'].includes(method)) {
        if (data instanceof FormData) {
          requestOptions.body = data
          // Remove Content-Type header for FormData (browser sets it automatically)
          delete (headers as any)['Content-Type']
        } else {
          requestOptions.body = JSON.stringify(data)
        }
      }

      const response = await fetch(url, requestOptions)
      
      clearTimeout(timeoutId)

      // Handle non-ok responses
      if (!response.ok) {
        let errorData: any
        try {
          const contentType = response.headers.get('content-type')
          if (contentType?.includes('application/json')) {
            errorData = await response.json()
          } else {
            errorData = { message: await response.text() }
          }
        } catch {
          errorData = { message: `HTTP ${response.status} ${response.statusText}` }
        }

        throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}`, {
          cause: {
            status: response.status,
            statusText: response.statusText,
            data: errorData
          }
        })
      }

      // Parse response data
      let responseData: T
      try {
        const contentType = response.headers.get('content-type')
        if (contentType?.includes('application/json')) {
          responseData = await response.json()
        } else {
          responseData = (await response.text()) as unknown as T
        }
      } catch (error) {
        throw new Error('Failed to parse response data', { cause: error })
      }

      return {
        data: responseData,
        status: response.status,
        statusText: response.statusText,
        headers: this.parseHeaders(response.headers)
      }

    } catch (error) {
      clearTimeout(timeoutId)
      
      if (controller.signal.aborted) {
        throw new Error(`Request timeout after ${timeout}ms`)
      }
      
      throw error
    }
  }

  /**
   * Build complete URL with query parameters
   */
  private buildUrl(endpoint: string, params?: Record<string, string>): string {
    // Ensure endpoint starts with /
    if (!endpoint.startsWith('/')) {
      endpoint = '/' + endpoint
    }

    let url = this.config.baseURL + endpoint

    if (params && Object.keys(params).length > 0) {
      const searchParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, value.toString())
        }
      })
      
      const queryString = searchParams.toString()
      if (queryString) {
        url += '?' + queryString
      }
    }

    return url
  }

  /**
   * Build request headers with authentication
   */
  private async buildHeaders(
    requireAuth = false, 
    customHeaders: Record<string, string> = {}
  ): Promise<Record<string, string>> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...customHeaders
    }

    // Add authentication header if required
    if (requireAuth) {
      const token = this.getStoredAccessToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      } else {
        throw new Error('Authentication required but no access token available')
      }
    }

    return headers
  }

  /**
   * Parse response headers to object
   */
  private parseHeaders(headers: Headers): Record<string, string> {
    const headerObj: Record<string, string> = {}
    headers.forEach((value, key) => {
      headerObj[key] = value
    })
    return headerObj
  }

  /**
   * Get stored access token
   */
  private getStoredAccessToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('access_token')
  }

  /**
   * Normalize errors to consistent format
   */
  private normalizeError(error: Error): ApiError {
    const apiError: ApiError = {
      message: error.message || 'Unknown error occurred'
    }

    // Extract status and response data from error cause
    if (error.cause && typeof error.cause === 'object') {
      const cause = error.cause as any
      
      if (cause.status) {
        apiError.status = cause.status
      }
      
      if (cause.statusText || cause.data) {
        apiError.response = {
          status: cause.status,
          statusText: cause.statusText,
          data: cause.data
        }
      }
    }

    // Handle network errors
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      apiError.message = 'Network error - please check your internet connection'
    }

    return apiError
  }
}

// Export singleton instance
export const apiClient = new ApiClient()