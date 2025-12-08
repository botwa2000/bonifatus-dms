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

// Entity types configuration for NER display
export const ENTITY_TYPES = {
  SENDER: { label: 'Sender', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
  RECIPIENT: { label: 'Recipient', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
  ORGANIZATION: { label: 'Organizations', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
  PERSON: { label: 'People', color: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200' },
  LOCATION: { label: 'Locations', color: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' },
  ADDRESS: { label: 'Addresses', color: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' },
  ADDRESS_COMPONENT: { label: 'Address Components', color: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' },
  EMAIL: { label: 'Email Addresses', color: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200' },
  URL: { label: 'Websites', color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200' }
} as const

// Helper functions
export const isDevelopment = () => appConfig.env === 'development'
export const isProduction = () => appConfig.env === 'production'
export const shouldLog = (type: 'debug' | 'error' = 'debug') => {
  if (type === 'debug') return appConfig.enableDebugLogs
  if (type === 'error') return appConfig.enableVerboseErrors
  return false
}
