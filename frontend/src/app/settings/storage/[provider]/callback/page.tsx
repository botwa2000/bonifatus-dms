// frontend/src/app/settings/storage/[provider]/callback/page.tsx
'use client'

import { useEffect, useState, useRef, Suspense } from 'react'
import { useRouter, useSearchParams, useParams } from 'next/navigation'
import { storageProviderService } from '@/services/storage-provider.service'
import { apiClient } from '@/services/api-client'
import { logger } from '@/lib/logger'

const PROVIDER_NAMES: Record<string, string> = {
  google_drive: 'Google Drive',
  onedrive: 'OneDrive',
  dropbox: 'Dropbox',
  box: 'Box'
}

function StorageCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const params = useParams()
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing')
  const [message, setMessage] = useState<string>('Connecting storage provider...')
  const hasProcessed = useRef(false)

  const provider = params.provider as string
  const providerName = PROVIDER_NAMES[provider] || provider

  useEffect(() => {
    // Prevent duplicate processing within same component instance
    if (hasProcessed.current) return
    hasProcessed.current = true

    const handleCallback = async () => {
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const error = searchParams.get('error')

      logger.debug(`[${providerName} Callback] Starting OAuth callback`, {
        provider,
        hasCode: !!code,
        hasState: !!state,
        error
      })

      // Handle OAuth error from provider
      if (error) {
        setStatus('error')
        setMessage(`Authentication failed: ${error}`)
        setTimeout(() => router.push('/settings'), 3000)
        return
      }

      // Validate required OAuth parameters
      if (!code || !state) {
        setStatus('error')
        setMessage('Missing authentication parameters')
        setTimeout(() => router.push('/settings'), 3000)
        return
      }

      // Update status message
      setMessage(`Connecting to ${providerName}...`)

      // Call backend to complete OAuth flow
      try {
        logger.debug(`[${providerName} Callback] Calling backend OAuth callback with code and state...`)

        const result = await storageProviderService.handleOAuthCallback(
          provider,
          code,
          state
        )

        logger.debug(`[${providerName} Callback] Backend response:`, result)

        if (result.success) {
          logger.debug(`[${providerName} Callback] ✅ Connection successful, refreshing auth tokens...`)

          // Refresh auth tokens to prevent logout after OAuth connection
          // OAuth flow can take time, and access token might be close to expiring
          try {
            logger.debug(`[${providerName} Callback] Calling /auth/refresh...`)
            await apiClient.post('/api/v1/auth/refresh', {}, true)
            logger.debug(`[${providerName} Callback] ✅ Auth tokens refreshed successfully`)
          } catch (refreshError) {
            logger.error(`[${providerName} Callback] ❌ Token refresh failed:`, refreshError)
            // Continue anyway - user might still be logged in with existing token
          }

          logger.debug(`[${providerName} Callback] Setting success status and redirecting to /settings in 2s...`)
          setStatus('success')
          setMessage(result.message || `${providerName} connected successfully!`)
          setTimeout(() => {
            logger.debug(`[${providerName} Callback] Executing router.push to /settings`)
            router.push('/settings')
          }, 2000)
        } else {
          logger.error(`[${providerName} Callback] ❌ Connection failed:`, result.message)
          setStatus('error')
          setMessage(result.message || `Failed to connect ${providerName}`)
          setTimeout(() => router.push('/settings'), 3000)
        }
      } catch (error) {
        logger.error(`[${providerName} Callback] ❌ Exception caught:`, error)
        setStatus('error')
        const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred'
        setMessage(errorMessage)
        logger.debug(`[${providerName} Callback] Redirecting to /settings in 3s after error`)
        setTimeout(() => router.push('/settings'), 3000)
      }
    }

    handleCallback()
  }, [searchParams, router, provider, providerName])

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50">
      <div className="max-w-md w-full p-8 bg-white rounded-lg shadow-lg text-center">
        {status === 'processing' && (
          <>
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-neutral-900 mb-2">
              Connecting {providerName}
            </h2>
            <p className="text-sm text-neutral-600">{message}</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="h-12 w-12 mx-auto mb-4 text-green-600">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-neutral-900 mb-2">Success!</h2>
            <p className="text-sm text-neutral-600">{message}</p>
            <p className="text-xs text-neutral-500 mt-2">Redirecting to settings...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="h-12 w-12 mx-auto mb-4 text-red-600">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-neutral-900 mb-2">Connection Failed</h2>
            <p className="text-sm text-neutral-600">{message}</p>
            <p className="text-xs text-neutral-500 mt-2">Redirecting to settings...</p>
          </>
        )}
      </div>
    </div>
  )
}

export default function StorageCallbackPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto mb-4"></div>
          <p className="text-sm text-neutral-600">Loading...</p>
        </div>
      </div>
    }>
      <StorageCallbackContent />
    </Suspense>
  )
}
