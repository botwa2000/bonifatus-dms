// frontend/src/lib/performance.ts
/**
 * Frontend Performance Monitoring Service
 * Tracks API calls, page loads, and component performance.
 * Logs are silent (console only in dev mode) and not exposed externally.
 */

// Environment flags
const isDev = process.env.NEXT_PUBLIC_DEBUG_LOGS === 'true'
const isProd = process.env.NODE_ENV === 'production'
const SLOW_API_THRESHOLD_MS = parseInt(process.env.NEXT_PUBLIC_SLOW_API_THRESHOLD_MS || '1000', 10)
const SLOW_PAGE_THRESHOLD_MS = parseInt(process.env.NEXT_PUBLIC_SLOW_PAGE_THRESHOLD_MS || '2000', 10)

interface ApiMetric {
  endpoint: string
  method: string
  durationMs: number
  status: number
  timestamp: Date
  requestId?: string
}

interface PageMetric {
  path: string
  durationMs: number
  timestamp: Date
}

class PerformanceMonitor {
  private apiMetrics: ApiMetric[] = []
  private pageMetrics: PageMetric[] = []
  private readonly maxHistory = 100

  /**
   * Record an API call metric
   */
  recordApiCall(
    endpoint: string,
    method: string,
    durationMs: number,
    status: number,
    requestId?: string
  ): void {
    const metric: ApiMetric = {
      endpoint,
      method,
      durationMs,
      status,
      timestamp: new Date(),
      requestId
    }

    // Store in history (circular buffer)
    this.apiMetrics.push(metric)
    if (this.apiMetrics.length > this.maxHistory) {
      this.apiMetrics.shift()
    }

    // Log slow requests
    if (durationMs > SLOW_API_THRESHOLD_MS) {
      this.logSlowApi(metric)
    } else if (isDev) {
      console.debug(
        `[PERF] ${method} ${endpoint} - ${durationMs.toFixed(0)}ms [${status}]`
      )
    }
  }

  /**
   * Record a page load metric
   */
  recordPageLoad(path: string, durationMs: number): void {
    const metric: PageMetric = {
      path,
      durationMs,
      timestamp: new Date()
    }

    this.pageMetrics.push(metric)
    if (this.pageMetrics.length > this.maxHistory) {
      this.pageMetrics.shift()
    }

    if (durationMs > SLOW_PAGE_THRESHOLD_MS) {
      this.logSlowPage(metric)
    } else if (isDev) {
      console.debug(`[PERF] Page ${path} loaded in ${durationMs.toFixed(0)}ms`)
    }
  }

  /**
   * Get current performance stats (for debugging)
   */
  getStats(): {
    apiCalls: {
      total: number
      avgDurationMs: number
      slowCount: number
    }
    pageLoads: {
      total: number
      avgDurationMs: number
      slowCount: number
    }
  } {
    const avgApiDuration = this.apiMetrics.length > 0
      ? this.apiMetrics.reduce((sum, m) => sum + m.durationMs, 0) / this.apiMetrics.length
      : 0

    const avgPageDuration = this.pageMetrics.length > 0
      ? this.pageMetrics.reduce((sum, m) => sum + m.durationMs, 0) / this.pageMetrics.length
      : 0

    return {
      apiCalls: {
        total: this.apiMetrics.length,
        avgDurationMs: Math.round(avgApiDuration),
        slowCount: this.apiMetrics.filter(m => m.durationMs > SLOW_API_THRESHOLD_MS).length
      },
      pageLoads: {
        total: this.pageMetrics.length,
        avgDurationMs: Math.round(avgPageDuration),
        slowCount: this.pageMetrics.filter(m => m.durationMs > SLOW_PAGE_THRESHOLD_MS).length
      }
    }
  }

  /**
   * Get recent slow API calls (for debugging)
   */
  getRecentSlowApiCalls(limit = 10): ApiMetric[] {
    return this.apiMetrics
      .filter(m => m.durationMs > SLOW_API_THRESHOLD_MS)
      .slice(-limit)
  }

  private logSlowApi(metric: ApiMetric): void {
    const message = `[SLOW API] ${metric.method} ${metric.endpoint} took ${metric.durationMs.toFixed(0)}ms (threshold: ${SLOW_API_THRESHOLD_MS}ms) [status=${metric.status}]`

    // In production, log as warning (will show in browser console)
    // In dev, log as console.warn so it stands out
    if (isProd) {
      // Silent in prod - only internal tracking
      // Could send to analytics service here if needed
    } else {
      console.warn(message)
    }
  }

  private logSlowPage(metric: PageMetric): void {
    const message = `[SLOW PAGE] ${metric.path} took ${metric.durationMs.toFixed(0)}ms (threshold: ${SLOW_PAGE_THRESHOLD_MS}ms)`

    if (isProd) {
      // Silent in prod
    } else {
      console.warn(message)
    }
  }

  /**
   * Clear all metrics (useful for testing)
   */
  clear(): void {
    this.apiMetrics = []
    this.pageMetrics = []
  }
}

// Singleton instance
export const performanceMonitor = new PerformanceMonitor()

/**
 * Timer utility for measuring duration
 */
export function createTimer(): { end: () => number } {
  const start = performance.now()
  return {
    end: () => Math.round(performance.now() - start)
  }
}

/**
 * Measure page load using Navigation Timing API
 */
export function measurePageLoad(): void {
  if (typeof window === 'undefined') return

  // Wait for page to fully load
  if (document.readyState === 'complete') {
    recordPageTiming()
  } else {
    window.addEventListener('load', recordPageTiming)
  }
}

function recordPageTiming(): void {
  // Use Navigation Timing API
  const timing = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming

  if (timing) {
    const loadTime = timing.loadEventEnd - timing.fetchStart
    if (loadTime > 0) {
      performanceMonitor.recordPageLoad(window.location.pathname, loadTime)
    }
  }
}

// Expose to window for debugging in dev
if (typeof window !== 'undefined' && isDev) {
  // @ts-expect-error - Expose for debugging
  window.__perfMonitor = performanceMonitor
}
