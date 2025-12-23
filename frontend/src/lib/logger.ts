// frontend/src/lib/logger.ts
/**
 * Centralized logging utility
 * Automatically handles dev vs production logging
 * - Debug/info logs only appear in development (controlled by NEXT_PUBLIC_DEBUG_LOGS)
 * - Warnings and errors always appear
 * - Production builds with debug disabled remove debug/info calls via dead code elimination
 */

const isDev = process.env.NEXT_PUBLIC_DEBUG_LOGS === 'true'

export const logger = {
  /**
   * Debug logging - only in development
   * Use for detailed debugging information
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  debug: (...args: any[]) => {
    if (isDev) console.log(...args)
  },

  /**
   * Info logging - only in development
   * Use for general informational messages
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  info: (...args: any[]) => {
    if (isDev) console.info(...args)
  },

  /**
   * Warning logging - always shown
   * Use for warnings that should be visible in production
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  warn: (...args: any[]) => {
    console.warn(...args)
  },

  /**
   * Error logging - always shown
   * Use for errors that should be visible in production
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  error: (...args: any[]) => {
    console.error(...args)
  },
}
