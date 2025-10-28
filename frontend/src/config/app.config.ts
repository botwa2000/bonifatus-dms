// frontend/src/config/app.config.ts
/**
 * Centralized application configuration
 * Single source of truth for environment-dependent settings
 */

interface AppConfig {
  env: 'development' | 'production'
  apiUrl: string
  enableDebugLogs: boolean
  enableVerboseErrors: boolean
}

// Read from environment variable or default to production
const ENV = (process.env.NEXT_PUBLIC_ENV || 'production') as 'development' | 'production'

export const appConfig: AppConfig = {
  env: ENV,
  apiUrl: process.env.NEXT_PUBLIC_API_URL || '',

  // Debug logging (set via NEXT_PUBLIC_DEBUG_LOGS=true)
  enableDebugLogs: process.env.NEXT_PUBLIC_DEBUG_LOGS === 'true',

  // Verbose error logging (set via NEXT_PUBLIC_VERBOSE_ERRORS=true)
  enableVerboseErrors: process.env.NEXT_PUBLIC_VERBOSE_ERRORS === 'true',
}

// Helper functions
export const isDevelopment = () => appConfig.env === 'development'
export const isProduction = () => appConfig.env === 'production'
export const shouldLog = (type: 'debug' | 'error' = 'debug') => {
  if (type === 'debug') return appConfig.enableDebugLogs
  if (type === 'error') return appConfig.enableVerboseErrors
  return false
}
