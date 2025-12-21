// frontend/src/lib/logger.ts
/**
 * Centralized logging utility
 * Automatically handles dev vs production logging
 * - Debug/info logs only appear in development
 * - Warnings and errors always appear
 * - Production builds automatically remove debug/info calls via dead code elimination
 */

const isDev = process.env.NODE_ENV === 'development'

export const logger = {
  /**
   * Debug logging - only in development
   * Use for detailed debugging information
   */
  debug: (...args: any[]) => {
    if (isDev) console.log(...args)
  },

  /**
   * Info logging - only in development
   * Use for general informational messages
   */
  info: (...args: any[]) => {
    if (isDev) console.info(...args)
  },

  /**
   * Warning logging - always shown
   * Use for warnings that should be visible in production
   */
  warn: (...args: any[]) => {
    console.warn(...args)
  },

  /**
   * Error logging - always shown
   * Use for errors that should be visible in production
   */
  error: (...args: any[]) => {
    console.error(...args)
  },
}
